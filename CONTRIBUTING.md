# Contributing Guidelines

We are grateful for your willingness to contribute to this project! We are interested in any features, bug fixes, new usage examples, etc.

## How to Contribute

1. Fork this repository, develop, and test your changes.
2. Submit a pull request.
3. Make sure all GitHub actions pass successfully.

***NOTE***: In order to make testing and merging of PRs easier, please submit changes for different fixes/features/improvements in separate PRs.

### Technical Requirements

* Must pass the CI job for linting. Please run `make lint` in the root of the project to know if the project complies with the requirements.
* New code must be covered by tests and pass the corresponding CI job. Please run `make test` in the root of the project.
* All changes require reviews from the responsible organization members before the merge.

Once changes have been merged, the release will be done by the responsible organization members.

## 🛠 Development

You can easily run the operator by following these steps:

1) Init the project and make changes. The project depends on [uv](https://docs.astral.sh/uv/getting-started/installation/); therefore, please make sure to install it first

```bash
make init-project
```


2) Create a Kubernetes cluster or change the `kubectl` context to the existing one.

```bash
make cluster
```


3) Build the operator image and load it into the cluster.

```bash
make docker-build
make docker-load
```

4) Deploy the helm chart with your image. If your changes require updating the Helm chart itself, please open a corresponding PR in this repository https://github.com/NCCloud/charts

```bash
helm repo add nccloud https://nccloud.github.io/charts
helm install netbox-resources-operator nccloud/netbox-resources-operator --set operatorConfig.netboxUrl="https://your-netbox-host" --set operatorConfig.netboxTokenSecretName="your-k8s-secret-with-read-write-netbox-token" --set image.tag="0.1.0-dev" # override the tag with the built image
```

Alternatively, configure the environment variables according to the [config file](app/config.py) and run the project.

```bash
export NAMESPACE="default"
kopf run main.py --verbose -A
```

5) Destroy the cluster once you are done testing your changes.

```bash
make cluster-delete
```
