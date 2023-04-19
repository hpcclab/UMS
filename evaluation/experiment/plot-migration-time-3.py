import json

import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np


def preprocess(path, d=0):
    with open(path) as f:
        data = json.load(f)

    memory = []
    downtime = []
    for row in data['0']:
        memory.append(max(row['memory'] - d, 0))  # going below 0 means it is in between iteration (nothing loaded)
        downtime.append(row['downtime'])
    return memory, downtime


fig = plt.subplots(figsize=(12, 6))

dind_memory, dind_downtime = preprocess('./dind/experiment3a.json')
ff_memory, ff_downtime = preprocess('./fastfreeze/experiment3a.json', 200)  # container memory - other processes memory
ssu_memory, ssu_downtime = preprocess('./ssu-podmigration-operator/experiment3a.json')

plt.scatter(ff_memory, ff_downtime, s=200, marker='^', c='darkgreen', label='Service-level approach')
plt.scatter(dind_memory, dind_downtime, s=200, marker='o', c='darkblue', label='Container-level approach')
plt.scatter(ssu_memory, ssu_downtime, s=200, marker='x', c='red', label='Orchestrator-level approach')

plt.xlabel('Container memory footprint (MB)', fontsize=24)
plt.ylabel('Downtime (seconds)', fontsize=24, labelpad=0)
plt.yticks(fontsize=18)
plt.xticks(fontsize=18)

a_val = 0.6
plt.legend(loc='best', prop={'size': 24})

plt.tight_layout()
plt.savefig('./migration_time_dynamic.pdf')
plt.show()
