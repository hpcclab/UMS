import json

import matplotlib.pyplot as plt
import matplotlib.patches as mp
import numpy as np


def preprocess(path, d=0):
    with open(path) as f:
        data = json.load(f)

    memory = []
    downtime = []
    migration_time = []
    for row in data['0']:
        memory.append(max(row['memory'] - d, 0))  # going below 0 means it is in between iteration (nothing loaded)
        downtime.append(row['downtime'])
        migration_time.append(row['overhead']['total'])
    return memory, downtime, migration_time


fig = plt.subplots(figsize=(12, 6))

dind_memory, dind_downtime, dind_migration_time = preprocess('./dind/experiment3a.json')
ff_memory, ff_downtime, ff_migration_time = preprocess('./fastfreeze/experiment3a.json', 200)  # container memory - other processes memory
ssu_memory, ssu_downtime, ssu_migration_time = preprocess('./ssu-podmigration-operator/experiment3a.json')

plt.scatter(ff_memory, ff_migration_time, s=200, marker='^', c='white', edgecolors='darkgreen', label='Service-level')
plt.scatter(dind_memory, dind_migration_time, s=200, marker='o', c='white', edgecolors='darkblue', label='Container-level')
plt.scatter(ssu_memory, ssu_migration_time, s=200, marker='+', c='red', label='Orchestrator-level')
plt.scatter(ff_memory, ff_downtime, s=200, marker='^', c='darkgreen', label='Service-level (downtime)')
plt.scatter(dind_memory, dind_downtime, s=200, marker='o', c='darkblue', label='Container-level (downtime)')
plt.scatter(ssu_memory, ssu_downtime, s=200, marker='x', c='red', label='Orchestrator-level (downtime)')


plt.xlabel('Container memory footprint (MB)', fontsize=24)
plt.ylabel('Migration time (seconds)', fontsize=24, labelpad=0)
plt.yticks(fontsize=18)
plt.xticks(fontsize=18)

a_val = 0.6
plt.legend(bbox_to_anchor=(0, 0.6, 0, 0), loc='center left', prop={'size': 22}, ncol=2)

plt.tight_layout()
plt.savefig('./migration_time_dynamic.pdf', bbox_inches='tight')
plt.show()
