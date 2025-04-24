from openshift import client, config


class OpenShiftHelper:
    def __init__(self, kubeconfig_path):
        config.load_kube_config(kubeconfig_path)
        self.api_instance = client.CoreV1Api()

    def list_pods(self, namespace="default"):
        pods = self.api_instance.list_namespaced_pod(namespace)
        return [pod.metadata.name for pod in pods.items]

    def create_namespace(self, namespace):
        body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        self.api_instance.create_namespace(body)
        return f"Namespace {namespace} created."
