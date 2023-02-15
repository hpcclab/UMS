import json

import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np


def preprocess(path):
    with open(path) as f:
        data = [element['overhead'] for element in json.load(f)]
    fields = ['creation', 'checkpoint_and_transfer_total', 'restoration', 'total']
    checkpoint_and_transfer_fields = ['checkpoint', 'checkpoint_files_transfer', 'checkpoint_files_delay',
                                      'image_layers_transfer',
                                      'image_layers_delay', 'file_system_transfer', 'file_system_delay',
                                      'volume_transfer', 'volume_delay']
    result = {
        field: sum([d[field] for d in data])/len(data)
        for field in fields
    }
    result['checkpoint_and_transfer'] = {
        field: sum([d['checkpoint_and_transfer'][field] for d in data])/len(data)
        for field in checkpoint_and_transfer_fields if data[0]['checkpoint_and_transfer'][field] is not None
    }
    return result


dind = preprocess('./dind/dind.json')
ff = preprocess('./fastfreeze/ff.json')
ssu = preprocess('./ssu-podmigration-operator/ssu.json')


barWidth = 0.1
fig = plt.subplots(figsize=(12, 6))


br1 = np.arange(6)
br2 = [x + barWidth for x in br1]
br3 = [x + barWidth for x in br2]
br4 = [x + barWidth for x in br3]
br5 = [x + barWidth for x in br4]
br6 = [x + barWidth for x in br5]
br7 = [x + barWidth for x in br6]

br8 = [x + barWidth/2 for x in br1]
br9 = [x + barWidth/2 for x in br3]


# Make the plot
plt.bar(br8, [ff['creation']]*6, color='none', width=barWidth*2, edgecolor='darkgreen', hatch='||')
plt.bar(br1, [ff['checkpoint_and_transfer']['checkpoint']]*6, color='none', width=barWidth,
        edgecolor='darkgreen', hatch='\\\\', bottom=[ff['creation']]*6)
plt.bar(br2, [ff['checkpoint_and_transfer']['checkpoint_files_transfer'] - ff['checkpoint_and_transfer']['checkpoint_files_delay']]*6, color='none', width=barWidth,
        edgecolor='darkgreen', hatch='//', bottom=[ff['creation'] + ff['checkpoint_and_transfer']['checkpoint_files_delay']]*6)
plt.bar(br8, [ff['restoration']]*6, color='none', width=barWidth*2,
        edgecolor='darkgreen', hatch='--', bottom=[ff['creation'] + ff['checkpoint_and_transfer_total']]*6)

plt.bar(br9, [ssu['creation']]*6, color='none', width=barWidth*2, edgecolor='red', hatch='||')
plt.bar(br3, [ssu['checkpoint_and_transfer']['checkpoint']]*6, color='none', width=barWidth,
        edgecolor='red', hatch='\\\\', bottom=[ssu['creation']]*6)
plt.bar(br4, [ssu['checkpoint_and_transfer']['checkpoint_files_transfer'] - ssu['checkpoint_and_transfer']['checkpoint_files_delay']]*6, color='none', width=barWidth,
        edgecolor='red', hatch='//', bottom=[ssu['creation'] + ssu['checkpoint_and_transfer']['checkpoint_files_delay']]*6)
plt.bar(br9, [ssu['restoration']]*6, color='none', width=barWidth*2,
        edgecolor='red', hatch='--', bottom=[ssu['creation'] + ssu['checkpoint_and_transfer_total']]*6)

plt.bar(br6, [dind['creation']]*6, color='none', width=barWidth*3, edgecolor='darkblue', hatch='||')
plt.bar(br5, [dind['checkpoint_and_transfer']['checkpoint']]*6, color='none', width=barWidth,
        edgecolor='darkblue', hatch='\\\\', bottom=[dind['creation']]*6)
plt.bar(br6, [dind['checkpoint_and_transfer']['checkpoint_files_transfer'] - dind['checkpoint_and_transfer']['checkpoint_files_delay']]*6, color='none', width=barWidth,
        edgecolor='darkblue', hatch='//', bottom=[dind['creation'] + dind['checkpoint_and_transfer']['checkpoint_files_delay']]*6)
plt.bar(br7, [dind['checkpoint_and_transfer']['file_system_transfer']]*6, color='none', width=barWidth,
        edgecolor='darkblue', hatch='+', bottom=[dind['creation'] + dind['checkpoint_and_transfer']['file_system_delay']]*6)
plt.bar(br6, [dind['restoration']]*6, color='none', width=barWidth*3,
        edgecolor='darkblue', hatch='--', bottom=[dind['creation'] + dind['checkpoint_and_transfer_total']]*6)

plt.xlabel('Container memory footprint (MiB)', fontsize=24)
plt.ylabel('Time (seconds)', fontsize=24, labelpad=0)
plt.yticks(fontsize=18)
plt.xticks([r + 3*barWidth for r in range(6)],
           ['0', '64', '128', '256', '512', '1024'], fontsize=18)

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
