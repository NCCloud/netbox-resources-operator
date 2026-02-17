#!/usr/bin/env bash

KIND_IMAGE="kindest/node:v1.35.0"
KIND_CLUSTER="netbox-resources-operator"
IMAGE_REGISTRY="ghcr.io/nccloud/netbox-resources-operator"
NETBOX_CHART_REPOSITORY="oci://ghcr.io/netbox-community/netbox-chart/netbox"
NETBOX_CHART_VERSION="7.2.26"
KUBECTL_CONTEXT="kind-netbox-resources-operator"
# NetBox chart generates a new token on every release without updating it in NetBox
# therefore, persist a token during the chart deployment
NETBOX_TOKEN="f82061ce-6e79-4e45-af70-417194bd47a1"

create_kind_cluster() {
  if ! kind get clusters | grep -q "^$KIND_CLUSTER$"; then
    echo "Creating kind cluster $KIND_CLUSTER..."
    kind create cluster --name "$KIND_CLUSTER" --image "$KIND_IMAGE"
  else
    echo "Cluster $KIND_CLUSTER already exists."
  fi
}

delete_kind_cluster() {
  kind delete cluster --name "$KIND_CLUSTER"
}


build_operator_image() {
  image="$IMAGE_REGISTRY:$(git log -1 --pretty=%h)-$(date +%s)"
  docker buildx build -t "$image" .
  echo "$image"
}

load_operator_image() {
  image="$1"
  kind load docker-image --name "$KIND_CLUSTER" "$image"
}

build_and_load_operator_image() {
  image=$(build_operator_image)
  load_operator_image "$image"
  echo "$image"
}

deploy_netbox_chart() {
  echo "Installing the NetBox chart. This may take a while..."
  helm upgrade --install --version "$NETBOX_CHART_VERSION" netbox \
    "$NETBOX_CHART_REPOSITORY" \
    --set superuser.apiToken="$NETBOX_TOKEN"\
    --wait \
    --timeout 10m
}

deploy_netbox_resources_operator() {
  image="$1"

  netbox_token=$(kubectl get secret netbox-superuser -o jsonpath='{.data.api_token}' | base64 --decode)
  secret_name="netbox-token"
  kubectl delete secret "$secret_name" || true
  kubectl create secret generic "$secret_name" --from-literal=token="$netbox_token"

  echo "Installing the netbox-resources-operator chart..."
  helm repo add nccloud https://nccloud.github.io/charts
  helm repo update nccloud
  helm upgrade --install netbox-resources-operator nccloud/netbox-resources-operator \
    --set operatorConfig.netboxUrl="http://netbox.default.svc.cluster.local" \
    --set operatorConfig.netboxTokenSecretName="$secret_name" \
    --set operatorConfig.operatorBackoffSeconds=1 \
    --set image.tag="$image" \
    --wait \
    --timeout 10m
}

prepare_dev_environment() {
  create_kind_cluster
  kubectl config use-context "$KUBECTL_CONTEXT"
  image=$(build_and_load_operator_image)
  image_tag=$(echo "$image" | cut -d: -f2)
  deploy_netbox_chart
  deploy_netbox_resources_operator "$image_tag"
}

"$@"
