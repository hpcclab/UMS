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


barWidth = 0.1
fig = plt.subplots(figsize=(12, 6))
x = ['0', '64', '128', '256', '512', '1024']

dind = preprocess('./dind/dind.json', x)
ff = preprocess('./fastfreeze/ff.json', x)
ssu = preprocess('./ssu-podmigration-operator/ssu.json', x)

br1 = np.arange(len(x))
br2 = [x + barWidth for x in br1]
br3 = [x + barWidth for x in br2]
br4 = [x + barWidth for x in br3]
br5 = [x + barWidth for x in br4]
br6 = [x + barWidth for x in br5]
br7 = [x + barWidth for x in br6]

br8 = [x + barWidth/2 for x in br1]
br9 = [x + barWidth/2 for x in br3]


# Make the plot
plt.bar(br8, [element['creation'] for element in ff], color='none', width=barWidth*2, edgecolor='darkgreen', hatch='||')
plt.bar(br1, [element['checkpoint_and_transfer']['checkpoint'] for element in ff], color='none', width=barWidth,
        edgecolor='darkgreen', hatch='\\\\', bottom=[element['creation'] for element in ff])
plt.bar(br2, [element['checkpoint_and_transfer']['checkpoint_files_transfer'] - element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in ff], color='none', width=barWidth,
        edgecolor='darkgreen', hatch='//', bottom=[element['creation'] + element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in ff])
plt.bar(br8, [element['restoration'] for element in ff], color='none', width=barWidth*2,
        edgecolor='darkgreen', hatch='--', bottom=[element['creation'] + element['checkpoint_and_transfer_total'] for element in ff])

plt.bar(br9, [element['creation'] for element in ssu], color='none', width=barWidth*2, edgecolor='red', hatch='||')
plt.bar(br3, [element['checkpoint_and_transfer']['checkpoint'] for element in ssu], color='none', width=barWidth,
        edgecolor='red', hatch='\\\\', bottom=[element['creation'] for element in ssu])
plt.bar(br4, [element['checkpoint_and_transfer']['checkpoint_files_transfer'] - element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in ssu], color='none', width=barWidth,
        edgecolor='red', hatch='//', bottom=[element['creation'] + element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in ssu])
plt.bar(br9, [element['restoration'] for element in ssu], color='none', width=barWidth*2,
        edgecolor='red', hatch='--', bottom=[element['creation'] + element['checkpoint_and_transfer_total'] for element in ssu])

plt.bar(br6, [element['creation'] for element in dind], color='none', width=barWidth*3, edgecolor='darkblue', hatch='||')
plt.bar(br5, [element['checkpoint_and_transfer']['checkpoint'] for element in dind], color='none', width=barWidth,
        edgecolor='darkblue', hatch='\\\\', bottom=[element['creation'] for element in dind])
plt.bar(br6, [element['checkpoint_and_transfer']['checkpoint_files_transfer'] - element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in dind], color='none', width=barWidth,
        edgecolor='darkblue', hatch='//', bottom=[element['creation'] + element['checkpoint_and_transfer']['checkpoint_files_delay'] for element in dind])
plt.bar(br7, [element['checkpoint_and_transfer']['file_system_transfer'] - element['checkpoint_and_transfer']['file_system_delay'] for element in dind], color='none', width=barWidth,
        edgecolor='darkblue', hatch='+', bottom=[element['creation'] + element['checkpoint_and_transfer']['file_system_delay'] for element in dind])
plt.bar(br6, [element['restoration'] for element in dind], color='none', width=barWidth*3,
        edgecolor='darkblue', hatch='--', bottom=[element['creation'] + element['checkpoint_and_transfer_total'] for element in dind])

plt.xlabel('Container memory footprint (MiB)', fontsize=24)
plt.ylabel('Time (seconds)', fontsize=24, labelpad=0)
plt.yticks(fontsize=18)
plt.xticks([r + 3*barWidth for r in range(len(x))],
           x, fontsize=18)

a_val = 0.6

circ1 = mp.Patch(facecolor='none', alpha=a_val, edgecolor='red', label='Baseline approach')
circ2 = mp.Patch(facecolor='none', alpha=a_val, edgecolor='darkblue', label='Container nesting approach')
circ3 = mp.Patch(facecolor='none', alpha=a_val, edgecolor='darkgreen', label='Init process approach')
circ4 = mp.Patch(facecolor='none', alpha=a_val, hatch='||', label='Creating dest. container')
circ5 = mp.Patch(facecolor='none', alpha=a_val, hatch=r'\\\\', label='Checkpointing')
circ6 = mp.Patch(facecolor='none', alpha=a_val, hatch='//', label='Ckpt. files transfer')
circ8 = mp.Patch(facecolor='none', alpha=a_val, hatch='+', label='RW layers transfer')
circ7 = mp.Patch(facecolor='none', alpha=a_val, hatch='--', label='Restoration')

# plt.legend(handles=[circ1, circ2, circ3, circ4, circ5, circ6, circ7], loc=2, prop={'size': 24})
plt.legend(handles=[circ1, circ2, circ3, circ4, circ5, circ6, circ8, circ7], loc=2, prop={'size': 24})


plt.tight_layout()
plt.savefig('./migration_time.pdf')
plt.show()
