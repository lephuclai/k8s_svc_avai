from variables import *
from kubernetes import client, config
import time
import sys
import paramiko

ENDPOINT = sys.argv[1]

# SSH to worker
def remote_worker_connect(host_username: str, host_ip: str, host_pass: str, event=None):
    print("Trying to connect to remote host {}, IP: {}".format(
        host_username, host_ip))
    try:
        global worker_client 
        worker_client = paramiko.SSHClient()
        worker_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        worker_client.connect(host_ip, username=host_username,
                       password=host_pass)
    except paramiko.AuthenticationException:
        print("Authentication failed when connecting to %s" % host_ip)
        sys.exit(1)
    except:
        print("Could not SSH to %s, waiting for it to start" % host_ip)
    if event is not None:
        event.set()

# Execute command in worker
def remote_worker_command(command: str):
    print(command)
    stdin, stdout, stderr = worker_client.exec_command(command, get_pty=True)
    # stdin.write(MEC_PASSWORD + '\n')
    stdin.flush()

    # Return output of executed command
    output = ""
    for line in stdout:
        output += line.strip('\n') + "\n"
    return output.strip()

# Load Kubernetes configuration
config.load_kube_config()

# Create CoreV1Api instance
v1 = client.CoreV1Api()

check_reaction = 0 #check if reaction time has been recorded
check_recover = 0 #check if recover time has been recorded

remote_worker_connect(MEC_USERNAME, MEC_IP, MEC_PASSWORD)

if sys.argv[2] == "pod":
    # Get POD ID
    pod_id = remote_worker_command("sudo crictl ps | grep detection1 | awk '{print $9}' | head -1")
    print("Pod ID: " + pod_id)

    # Get PID of pod
    PID = remote_worker_command("pstree -a -p --long | grep " + pod_id + " | cut -f 2 -d ',' | cut -f 1 -d ' ' | head -1")
    print("Pod PID: " + PID)

# # Kill container using crictl
# elif sys.argv[2] == "container":
#     container_id = remote_worker_command("sudo crictl ps | grep detection1 | awk '{print $1}' | head -1")
#     print("Container ID: " + container_id)
#     start = time.time()
#     remote_worker_command("sudo crictl stop " + container_id)

# Kill container using PID
elif sys.argv[2] == "container":
    # Get POD ID
    pod_id = remote_worker_command("sudo crictl ps | grep detection1 | awk '{print $9}' | head -1")
    print("Pod ID: " + pod_id)
    #Get PID of pod
    pod_PID = remote_worker_command("pstree -a -p --long | grep " + pod_id + " | cut -f 2 -d ',' | cut -f 1 -d ' ' | head -1")
    print("Pod PID: " + pod_PID)
    # Get PID of Container
    PID = remote_worker_command("pstree -a -p --long " + pod_PID + " | awk '/python3/{split($1, a, " + '","' + "); print a[2]}' | head -1")
    print("Container PID: " + PID)


# elif sys.argv[2] == "process":
#     pod_id = remote_worker_command("sudo crictl ps | grep detection1 | awk '{print $9}' | head -1")
#     print("Pod ID: " + pod_id)
#     pod_PID = remote_worker_command("pstree -a -p --long | grep " + pod_id + " | cut -f 2 -d ',' | cut -f 1 -d ' ' | head -1")
#     print("Pod PID: " + pod_PID)
#     PID = remote_worker_command("pstree -a -p --long " + pod_PID + " | grep '{python3}' | cut -d ',' -f2 | cut -d '}' -f1 | head -1")
#     print("Process ID: " + PID)

start = time.time() #Get current epoch time
remote_worker_command("sudo kill -9 -1 " + PID) #kil pod/container/process

while True:
    # Read endpoints for the nginx-service in the default namespace 
    ## Change endpoint name and namespace
    ret = v1.read_namespaced_endpoints(ENDPOINT, NAMESPACE, pretty=True)

    # Extract subsets from the result
    res = ret.subsets

    # Iterate through the subsets
    for subset in res:
        
        # Check if whether service's IP address is listed in endpoints or not
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
        worker_client.close()
        break