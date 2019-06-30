## Description
Illustrate traffic control using label in Kubernetes with Istio
There are two version of control.
- Version 1 is binary control which only send requrest to pods with label "status=normal".
- Version 2 distribute requests to 3 subsets according to status label.
## Deployment
1. Install Minikube/Istio
2. Build demo app(hostname) image in "src/hostname-app/" and make it available to minikube vm(currently, the demo using local image).
  - eval $(minikube docker-env)
  - cd src/hostname-app/
  - docker build -t hostname .
3. Deploy configuration
  - cd to root of repository
  - To deploy version 1, using: ./deploy
  - To deploy version 2, using: ./deploy -2
## Remove
1. remove configuration
  - cd to root of repository
  - ./deploy -d
## Version 1 control
All control can be done under the root of repository
1. Change status of intended pod
  - ./cmdshell.py setStatus <pod name> <normal|busy>
2. Test request ditribution
  - ./tstdis <number of requests, default 500>
## Version 2 control
All control can be done under the root of repository
1. Change status of intended pod
  - ./cmdshell.py setStatus <pod name> <idle|normal|busy>
2. Test request ditribution(if there's no idle or busy pods, istio will return failure)
  - ./tstdis <number of requests, default 500>
## Scale # of pods in deploymnet
1. Change number of intended pod
  - ./cmdshell.py scale <deployment name> <# of pods>
