from kubernetes import client, config

class cmd:
    def __init__(self):
        config.load_kube_config()
        self.coreApi = client.CoreV1Api()
        self.appsApi = client.AppsV1Api()

    def setStatus(self, pod, status, namespace="default"):
        print("Set status of " + namespace + "." + pod + " to " + status)
        body = {
            "metadata": {
                "labels": {
                    "status": status
                }
            }
        }
        ret = self.coreApi.patch_namespaced_pod(pod, namespace, body)
        #print(ret)

    def scale(self, deployment, nPods, namespace="default"):
        print("Set # of replicas of " + namespace + "." + deployment + " to " + nPods)
        body = {
            "spec": {
                "replicas": int(nPods)
            }
        }
        ret = self.appsApi.patch_namespaced_deployment_scale(deployment, namespace, body)

    def listAllPods(self):
        ret = self.coreApi.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
