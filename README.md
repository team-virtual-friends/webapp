# backend-service

https://medium.com/google-cloud/a-guide-to-deploy-flask-app-on-google-kubernetes-engine-bfbbee5c6fb

## Build Image
```sh
gcloud builds --project ysong-chat submit --tag gcr.io/ysong-chat/flask-app:$(git rev-parse --short HEAD) .
```

## Scale
```sh
kubectl scale deployment virtual-friends --replicas=NUMBER
kubectl autoscale deployment virtual-friends --min=NUMBER --max=NUMBER --cpu-ratio=FLOAT --replicas=NUMBER
```

## Redploy
Modify the kubernetes/deployment.yaml's image to be the `IMAGES` output by the Build Image step.
```sh
kubectl apply -f kubernetes/deployment.yaml
```
