from datetime import timedelta
from airflow import DAG
from kubernetes.client import models as k8s
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from resources.seqtender.gatk import generate_gatk_local_command
import time

# fixme https://github.com/apache/airflow/issues/16290 - after solving retries shouldn't be necessary

dag_run_uuid = "aba82c40-521a-4938-bfaa-0890d969091c"
push_gateway_address = "10.27.249.163:9091"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}
with DAG(
    dag_id="ngs-pipeline-aba82c40-521a-4938-bfaa-0890d969091c",
    default_args=default_args,
    description='NGS pipeline',
    schedule_interval=None,
    is_paused_upon_creation=False,
    start_date=days_ago(1),
    tags=['ngs'],
    params={
      'labels': {
        'job_uuid': dag_run_uuid
      }
    }
) as dag:
    def send_prom_metrics(push_gateway_address, **kwargs):
        from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
        registry = CollectorRegistry()
        labelnames = ['executor_instances', 'executor_memory', 'driver_memory', 'machine_type'] + ["job_uuid"]
        g = Gauge('k8s_cluster_setup', 'GKE cluster setup', labelnames=labelnames, registry=registry)
        g.labels(executor_instances="1",executor_memory="512m",driver_memory="1024m",machine_type="n1-standard-4", job_uuid=dag_run_uuid).set(time.time())
        push_to_gateway(push_gateway_address, job=str(dag_run_uuid), registry=registry)


    prom_sender = PythonOperator(
        dag=dag,
        task_id='send_cluster_setup_to_prometheus',
        python_callable=send_prom_metrics,
        op_kwargs={'push_gateway_address': push_gateway_address}
    )

    alignment = SparkKubernetesOperator(
        task_id='alignment',
        namespace='default',
        kubernetes_conn_id="kubernetes_default",
        application_file="resources/seqtender/alignment-aba82c40-521a-4938-bfaa-0890d969091c.yaml",
        do_xcom_push=True,
        retries=8,
        retry_delay=timedelta(seconds=30),
        dag=dag
    )

    alignment_monitoring = SparkKubernetesSensor(
        task_id='alignment-monitoring',
        namespace="default",
        application_name="{{ task_instance.xcom_pull(task_ids='alignment')['metadata']['name'] }}",
        kubernetes_conn_id="kubernetes_default",
        dag=dag
    )

    gatk_command = generate_gatk_local_command(bucket="gs://tbd-2021l-125-test-data", vcf_file="/vcf/mother10.vcf",
                                               ref_file="/home/ref/ref.fasta", bam_file="/bam/mother10.bam")

    variant_calling = KubernetesPodOperator(
        namespace='default',
        image='eu.gcr.io/tbd-2021l-125/tbd-gatk:v0.1',
        image_pull_secrets=[k8s.V1LocalObjectReference('spark-jobs-sa-credentials')],
        cmds=["bash", "-cx", gatk_command],
        labels={"tbd": "variant_calling"},
        name="variant_calling_gatk",
        is_delete_operator_pod=False,
        in_cluster=True,
        task_id="variant_calling",
        get_logs=True,
        env_vars=[k8s.V1EnvVar('SPARK_LOCAL_HOSTNAME', 'localhost')],
        log_events_on_failure=True,
        retry_delay=timedelta(minutes=1),
        image_pull_policy='Always'
    )

    annotation = SparkKubernetesOperator(
        task_id='annotation',
        namespace='default',
        kubernetes_conn_id="kubernetes_default",
        application_file="resources/seqtender/annotation-aba82c40-521a-4938-bfaa-0890d969091c.yaml",
        do_xcom_push=True,
        retries=8,
        retry_delay=timedelta(seconds=30),
        dag=dag
    )

    annotation_monitoring = SparkKubernetesSensor(
        task_id='annotation-monitoring',
        namespace="default",
        application_name="{{ task_instance.xcom_pull(task_ids='annotation')['metadata']['name'] }}",
        kubernetes_conn_id="kubernetes_default",
        # fixme when executor pods are created in two different nodes than this issue appears and job hangs: Warning
        #  FailedAttachVolume  2s (x8 over 111s)  attachdetach-controller  AttachVolume.Attach failed for volume
        #  "pvc-570c1dfb-f909-4ade-b213-453584bf6136" : googleapi: Error 400: RESOURCE_IN_USE_BY_ANOTHER_RESOURCE -
        #  The disk resource 'projects/tbd-2021l-125/zones/europe-west1-b/disks/gke-tbd-gke-cluster-57-pvc-570c1dfb-f909-4ade-b213-453584bf6136'
        #  is already being used by 'projects/tbd-2021l-125/zones/europe-west1-b/instances/gke-tbd-gke-cluster-tbd-lab-pool-16820644-0xbr'
        #  no good solution yet? https://github.com/kubernetes/kubernetes/issues/48968 / https://stackoverflow.com/questions/64393551/problems-mounting-persistent-volume-as-readonlymany-across-multiple-pods
        #  https://cloud.google.com/sdk/gcloud/reference/compute/instances/detach-disk
        retries=0,
        execution_timeout=timedelta(minutes=2, seconds=30),
        dag=dag
    )

    prom_sender >> alignment >> alignment_monitoring >> variant_calling >> annotation >> annotation_monitoring
