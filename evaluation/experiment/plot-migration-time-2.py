import json

import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np


def preprocess(path, key_list):
    with open(path) as f:
        data = {k: [element['overhead'] for element in v] for k, v in json.load(f).items()}
    fields = ['creation', 'checkpoint_and_transfer_total', 'restoration', 'total']
    checkpoint_and_transfer_fields = ['checkpoint', 'checkpoint_files_transfer', 'checkpoint_files_delay',
                                      'image_layers_transfer',
                                      'image_layers_delay', 'file_system_transfer', 'file_system_delay',
                                      'volume_transfer', 'volume_delay']
    result = []
    for key in key_list:
        result.append({
            field: sum([element[field] for element in data[key]])/len(data[key])
            for field in fields
        })
        result[-1]['checkpoint_and_transfer'] = {
            field: sum([element['checkpoint_and_transfer'][field] for element in data[key]])/len(data[key])
            for field in checkpoint_and_transfer_fields if data[key][0]['checkpoint_and_transfer'][field] is not None
        }
    return result


barWidth = 0.2
fig = plt.subplots(figsize=(12, 6))
# x = ['0', '4', '16', '64', '128', '256', '512', '1024']
x = [str(i) for i in range(1, 9)]
#
# dind = preprocess('./dind/experiment1.json', x)
# ff = preprocess('./fastfreeze/experiment1.json', x)
# ssu = preprocess('./ssu-podmigration-operator/experiment1.json', x)

dind = preprocess('./dind/experiment2.json', x)
ff = preprocess('./fastfreeze/experiment2.json', x)
ssu = preprocess('./ssu-podmigration-operator/experiment2.json', x)

# dind = preprocess('./dind/experiment3.json', x)
# ff = preprocess('./fastfreeze/experiment3.json', x)
# ssu = preprocess('./ssu-podmigration-operator/experiment3.json', x)

# x = ['≈0', '4', '16', '64', '128', '256', '512', '1024']
br1 = np.arange(len(x))
br2 = [x + barWidth for x in br1]
br3 = [x + barWidth for x in br2]
# br4 = [x + barWidth for x in br3]
# br5 = [x + barWidth for x in br4]
# br6 = [x + barWidth for x in br5]
# br7 = [x + barWidth for x in br6]
#
# br8 = [x + barWidth/2 for x in br1]
# br9 = [x + barWidth/2 for x in br3]


# Make the plot
plt.bar(br1, [element['creation'] + element['checkpoint_and_transfer_total'] + element['restoration'] for element in ff], color='none', width=barWidth, edgecolor='darkgreen', hatch='--')
plt.bar(br2, [element['creation'] + element['checkpoint_and_transfer_total'] + element['restoration'] for element in ssu], color='none', width=barWidth, edgecolor='red', hatch='\\\\')
plt.bar(br3, [element['creation'] + element['checkpoint_and_transfer_total'] + element['restoration'] for element in dind], color='none', width=barWidth, edgecolor='darkblue', hatch='//')

plt.yscale('log')
plt.ylim(bottom=1)
# plt.xlabel('Container memory footprint (MiB)', fontsize=24)
plt.xlabel('Number of processes', fontsize=24)
plt.ylabel('Migration time (seconds)', fontsize=24, labelpad=0)
plt.yticks(fontsize=18)
# plt.xticks([r + 3*barWidth for r in range(len(x))],
#            x, fontsize=18)
plt.xticks([r + barWidth for r in range(len(x))],
           x, fontsize=18)

a_val = 0.6

circ1 = mp.Patch(facecolor='white', alpha=a_val, edgecolor='red', hatch='\\\\', label='Orchestrator-level approach')
circ2 = mp.Patch(facecolor='white', alpha=a_val, edgecolor='darkblue', hatch='//', label='Container-level approach')
circ3 = mp.Patch(facecolor='white', alpha=a_val, edgecolor='darkgreen', hatch='--', label='Service-level approach')
# circ4 = mp.Patch(facecolor='white', alpha=a_val, hatch='||', label='Creating dest. container')
# circ5 = mp.Patch(facecolor='white', alpha=a_val, hatch=r'\\\\', label='Checkpointing')
# circ6 = mp.Patch(facecolor='white', alpha=a_val, hatch='//', label='Ckpt. files transfer')
# circ8 = mp.Patch(facecolor='white', alpha=a_val, hatch='+', label='RW layers transfer')
# circ7 = mp.Patch(facecolor='white', alpha=a_val, hatch='--', label='Restoration')

# plt.legend(handles=[circ1, circ2, circ3, circ4, circ5, circ6, circ7], loc=2, prop={'size': 24})
# plt.legend(handles=[circ3, circ1, circ2, circ4, circ5, circ6, circ8, circ7], loc=2, prop={'size': 20})
plt.legend(handles=[circ3, circ1, circ2], loc=2, prop={'size': 20})


plt.tight_layout()
# plt.savefig('./migration_time.pdf', bbox_inches='tight')
plt.savefig('./migration_time_2.pdf', bbox_inches='tight')
# plt.savefig('./migration_time_3.pdf', bbox_inches='tight')
plt.show()
