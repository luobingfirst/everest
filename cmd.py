import yaml
import time
from kubernetes import client, config

class cmd:
    def __init__(self):
        config.load_kube_config()
        self.coreApi = client.CoreV1Api()
        self.appsApi = client.AppsV1Api()
        self.customObjectsApi = client.CustomObjectsApi()

    def getPercentFromWeight(self, selector, weight, namespace="default", adjusts={}):
        """
        Get percent according to weight policy

        :param selector: The selecotr for all pods.
        :type: String
        
        :param weight: The target weight, with subset(category) name as keys and related weight as value, e.g.{"idle":30,"normal":50, "busy":20}. Be sure that it cover all category but the sum is not necessary to be 100.
        :type: Dict
        
        :param namespace: The namespace of pods.
        :type: String
        
        :para adjusts: Adjust the number of pods in specified categories, with subset(category) name as keys and number of pods(could be positive or negative) as value.
        :type: Dict
        
        :return: percent and ditribution
        :rtype: Dict
        """
        #get number of pods for each category, stored in distribution
        if (len(selector)>0):
            selector = selector + ", "
        distribution = {}
        dissum = 0
        for k,v in weight.items() :
            category = selector + "status=" + k
            pods = self.coreApi.list_namespaced_pod(namespace, label_selector=category, watch=False)
            pods = pods.items
            distribution[k] = len(pods)
            dissum = dissum + (v*distribution[k])
        nPods = sum(distribution.values())
        if (nPods <=0):
            return
        #print("adjusts : " + str(adjusts))
        #print("ditribution : " + str(distribution))
        #print("sum of effective percent : "+str(dissum))
        #print("target weight" + str(weight))

        #adjust ditribution and percent
        for k,v in adjusts.items():
            distribution[k] = distribution[k] + v
            dissum = dissum + v*weight[k]

        #calculate percent
        percent = {}
        for k,v in distribution.items():
            percent[k] = int(v*weight[k]*100/dissum)
        #make sure the sum of percent is 100
        res = 100 - sum(percent.values())
        lastKey = percent.keys()[len(percent)-1]
        percent[lastKey] = percent[lastKey] + res
        print("target percent : " + str(percent))
        
        return ({"percent":percent, "distribution":distribution})

    def scaleWithWeightPolicy(self, deployment, nPods, vsName, selector, weight, namespace="default"):
        """
        Scale # of pods and change percent according to weight policy

        :param deployment: The name of deployment.
        :type: String
        
        :param nPods: Number of pods in deployment.
        :type: String/Int
        
        :param vsName: The name of virtual service.
        :type: String
        
        :param selector: The selecotr for all pods.
        :type: String
        
        :param weight: The target weight, with subset(category) name as keys and related weight as value, e.g.{"idle":30,"normal":50, "busy":20}. Be sure that it cover all category but the sum is not necessary to be 100.
        :type: Dict
        
        :param namespace: The namespace of pods.
        :type: String
        """
        self.scale(deployment, nPods, namespace)
        time.sleep(1)
        ret = self.getPercentFromWeight(selector, weight, namespace)
        percent = ret["percent"]
        self.patchVSWeight(vsName, percent, namespace)

    def changeStatusWithWeightPolicy(self, pod, status, vsName, selector, weight, namespace="default"):
        """
        Set status and change percent according to weight policy

        :param pod: The name of pod.
        :type: String
        
        :param status: The target status of pod.
        :type: String
        
        :param vsName: The name of virtual service.
        :type: String
        
        :param selector: The selecotr for all pods.
        :type: String
        
        :param weight: The target weight, with subset(category) name as keys and related weight as value, e.g.{"idle":30,"normal":50, "busy":20}. Be sure that it cover all category but the sum is not necessary to be 100.
        :type: Dict
        
        :param namespace: The namespace of pods.
        :type: String
        """
        #get original status of the pod
        thePodInfo = self.coreApi.list_namespaced_pod(namespace, field_selector="metadata.name="+pod, watch=False)
        if (len(thePodInfo.items)<0):
            return
        thePod = thePodInfo.items[0]
        thePodStatus = thePod.metadata.labels["status"]
        if (thePodStatus == status):
            return

        ret = self.getPercentFromWeight(selector, weight, namespace, {thePodStatus:-1, status:1})
        percent = ret["percent"]
        distribution = ret["distribution"]
        
        #the order of set pod status and modify vs matters
        #   only "thePodStatus" category may change from 1 to 0 (category descrease)
        #   only target "status" category may change from 0 to 1 (category increase)
        #   IF only category descrease, modify first and set second
        #   IF only category increase, set first and modify second
        #   IF both, modify 1 to 0, set, modify 0 to 1
        #       Since the percent is the final state, we need to change it to middle state in thrid case
        #   To combine case, we can do the following:
        #       1) modify to X if category descrease, X is final state if no category increase, otherwise X is middle state
        #       2) set state
        #       3) modify to final state if category increase
        tmpPod = ""
        for k,v in percent.items():
            if (not (k==status or k==thePodStatus) and v>0):
                tmpPod = k
                break
        pStatus = percent[status]
        if (distribution[thePodStatus]==0):
            if (distribution[status]==1):
                if (not tmpPod==""):
                    percent[status] = 0
                    percent[tmpPod] = percent[tmpPod] + pStatus
                    self.patchVSWeight(vsName, percent, namespace)
            else:
                self.patchVSWeight(vsName, percent, namespace)
        self.setStatus(pod, status, namespace)
        if (distribution[status]==1):
            if (distribution[thePodStatus]==0 and not tmpPod==""):
                percent[status] = pStatus
                percent[tmpPod] = percent[tmpPod] - pStatus
            self.patchVSWeight(vsName, percent, namespace)

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

    def deployVS(self, yamlFile, namespace="default"):
        version = "v1alpha3"
        group = "networking.istio.io"
        plural = "virtualservices"
        #body = yaml.load(open(yamlFile))
        body = list(yaml.safe_load_all(open(yamlFile)))[0]
        ret = self.customObjectsApi.create_namespaced_custom_object(group, version, namespace, plural, body)
        #print(ret)

    def deployDR(self, yamlFile, namespace="default"):
        version = "v1alpha3"
        group = "networking.istio.io"
        plural = "destinationrules"
        #body = yaml.load(open(yamlFile))
        body = list(yaml.safe_load_all(open(yamlFile)))[0]
        ret = self.customObjectsApi.create_namespaced_custom_object(group, version, namespace, plural, body)
        #print(ret)

    def patchVSWeight(self, vsName, percent, namespace="default"):
        """
        Change the percent(weight in vs) of vs

        :param vsName: The name of virtual service.
        :type: String
        
        :param percent: The weight to modify with subset name as keys and related percent as value, e.g.{"idle":30,"normal":50}. Be sure that the sum of resulted weight should be exact 100 or this function will fail
        :type: Dict
        
        :param namespace: The namespace of virtual service.
        :type: String
        """
        print("change "+ vsName + " weight to " + str(percent))
        version = "v1alpha3"
        group = "networking.istio.io"
        plural = "virtualservices"
        vs = self.customObjectsApi.get_namespaced_custom_object(group, version, namespace, plural, vsName)
        for rule in vs["spec"]["http"]:
            for route in rule["route"]:
                category = route["destination"]["subset"]
                newWeight = percent.get(category, -1)
                if ( newWeight >= 0 ):
                    route["weight"] = newWeight
        #print(vs)
        self.customObjectsApi.patch_namespaced_custom_object(group, version, namespace, plural, vsName, vs)