from kubernetes import client, config
import time
import sys
import os

# Load Kubernetes configuration
config.load_kube_config()

# Create CoreV1Api instance
v1 = client.CoreV1Api()

process = sys.argv[1]
check_reaction = 0 #
check_recover = 0


start = time.time()
os.system("sudo kill " + sys.argv[1])

while True:
    # Read endpoints for the nginx-service in the default namespace
    ret = v1.read_namespaced_endpoints("nginx-service", "default", pretty=True)

    # Extract subsets from the result
    res = ret.subsets

    # Iterate through the subsets
    for subset in res:
        
        if subset.addresses is None and check_reaction == 0:
            reation_time = time.time() - start
            print("Reaction time: " + str(reation_time))
            check_reaction = 1
    
        elif check_reaction == 1 and subset.addresses is not None:
            recovery_time = time.time() - start - reation_time
            print("Recovery time: " + str(recovery_time))
            check_recover = 1
            break

    if check_recover == 1:
        break