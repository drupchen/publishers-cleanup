from pathlib import Path
import yaml
import json
import csv


def export_work_publisher():
    data = csv.reader(Path('publishers_GID.csv').open())
    data = list(data)

    out = 'workRID,locationRID\n'
    for d in data[1:]:
        work = d[4].split('=')[1]
        location = ','.join(d[1].split('\t'))
        out += f'{work},{location}\n'

    Path('work-publisherPlaceRID.csv').write_text(out)


def generate_new_places():
    content = Path('locations_cleaned_GID.tsv').read_text(encoding='utf-8-sig').strip().split('\n')
    content = content[1:]  # delete root

    previous = ''
    current = ''
    total = {}
    RID = {'key': '', 'langs': {}}
    current_lang = {'tag': '', 'strings': {}}
    for num, line in enumerate(content):
        # update state
        if line.startswith('\t\t\t'):
            current = 'lang_str'
        elif line.startswith('\t\t'):
            current = 'lang_tag'
        elif line.startswith('\t'):
            current = 'RID'
        else:
            raise SyntaxError(f'line {num}: "{line}" is not well formatted')

        # fill content
        line = line.strip()
        if current == 'RID':
            if previous == 'lang_str':
                RID['langs'][current_lang['tag']] = current_lang['strings']  # update
                current_lang = {'tag': '', 'strings': {}}  # reinitialize

                langs = {}
                for lang, strs in RID['langs'].items():
                    for k, v in RID['langs'][lang].items():
                        langs[k] = v
                total[RID['key']] = {'isLocatedIn': '', 'langs': langs}
                RID = {'key': '', 'langs': {}}
            RID['key'] = line
        if current == 'lang_tag':
            if previous == 'lang_str':
                RID['langs'][current_lang['tag']] = current_lang['strings']  # update
                current_lang = {'tag': '', 'strings': {}}  # reinitialize
            current_lang['tag'] = line
        if current == 'lang_str':
            lang_tag = ''
            if current_lang['tag'] == 'en':
                lang_tag = 'en'
            elif current_lang['tag'] == 'zh':
                lang_tag = 'zh-Hans'
            elif current_lang['tag'] == 'bo':
                lang_tag = 'bo-x-ewts'

            current_lang['strings'][line] = lang_tag

        previous = current

    # last element
    langs = {}
    for lang, strs in RID['langs'].items():
        for k, v in RID['langs'][lang].items():
            langs[k] = v
    total[RID['key']] = {'isLocatedIn': '', 'langs': langs}

    located_in = sorted([f'{k},' for k in list(total.keys())])
    Path('located_in_raw.txt').write_text('\n'.join(located_in))

    dump = Path('RID_node_modifs.csv').read_text().strip().split('\n')
    loc_info = []
    for line in dump[1:]:
        if not line:
            continue

        items = line.split(',')
        modif = items[2]

        loc_info.append((items[0], items[1], modif))


    # extend total with missing entries
    missing = json.loads(Path('missing_RIDs.json').read_text(encoding='utf-8-sig'))
    total.update(missing)

    # cleanup any previous isLocatedIn data
    for rid in total:
        if 'isLocatedIn' in total[rid].keys():
            total[rid]['isLocatedIn'] = ''

    extra_nodes = ['RID,isLocatedIn,modif type']
    for contained, container, modif in loc_info:
        if contained in total.keys():
            total[contained]['isLocatedIn'] = container
            total[contained]['node_modif'] = modif
        else:
            extra_nodes.append(f'{contained},{container},{modif}')
    Path('newExtraNodes.txt').write_text('\n'.join(extra_nodes), encoding='utf-8-sig')

    # delete multiple locations entries
    keys = list(total.keys())
    for key in keys:
        if '\t' in key or '(etc.)' in key:
            del total[key]

    return total


def find_remaining_RIDs(total):
    # find and process all the remaining RIDs that are either in matches.csv or needs_attribution.csv
    # or in work-publisherPlaceRID.csv and that don't yet have an entry in newPlaceRIDs.json
    total_RIDs = Path('work-publisherPlaceRID.csv').read_text(encoding='utf-8-sig').strip().split('\n')[1:]
    total_RIDs = set([a for line in total_RIDs for a in line.split(',')[1:]])

    missing_rids = [t for t in total_RIDs if t not in total]

    others = {}
    matches = Path('output/matches.csv').read_text(encoding='utf-8-sig').strip().split('\n')
    for m in matches:
        name, rid = m.split(',')
        others[rid] = name

    news = Path('output/needs_attribution.csv').read_text(encoding='utf-8-sig').strip().split('\n')
    for m in news:
        name, rid = m.split(',')
        others[rid] = name


    new_entries = {}
    new_pairs = {rid: name for rid, name in others.items() if rid not in total and '\t' not in rid and 'etc.' not in rid}
    for rid, name in new_pairs.items():
        new = {'isLocatedIn': '', 'langs': {name: ''}}
        new_entries[rid] = new
    new_json = json.dumps(new_entries, ensure_ascii=False, indent=4, sort_keys=True)
    Path('missing_RIDs_raw.json').write_text(new_json, encoding='utf-8-sig')

    # after adding them to total, write total
    out = json.dumps(total, ensure_ascii=False, indent=4, sort_keys=True)
    Path('newPlaceRIDs_raw.json').write_text(out, encoding='utf-8-sig')


total = generate_new_places()
export_work_publisher()
find_remaining_RIDs(total)