from datetime import timedelta
from airflow import DAG
from kubernetes.client import models as k8s
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from resources.seqtender.gatk import generate_gatk_local_command

# 42

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
    'ngs-pipeline',
    default_args=default_args,
    description='NGS pipeline',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(1),
    tags=['ngs'],
) as dag:
    alignment = SparkKubernetesOperator(
        task_id='alignment',
        namespace='default',
        kubernetes_conn_id="kubernetes_default",
        application_file="resources/seqtender/alignment.yaml",
        do_xcom_push=True,
        dag=dag
    )

    alignment_monitoring = SparkKubernetesSensor(
        task_id='alignment-monitoring',
        namespace="default",
        application_name="{{ task_instance.xcom_pull(task_ids='alignment')['metadata']['name'] }}",
        kubernetes_conn_id="kubernetes_default",
        dag=dag
    )

    gatk_command = generate_gatk_local_command(bucket="gs://tbd-2021l-123-test-data", vcf_file="/vcf/mother10.vcf",
                                               ref_file="/home/ref/ref.fasta", bam_file="/bam/mother10.bam")

    variant_calling = KubernetesPodOperator(
        namespace='default',
        image='eu.gcr.io/tbd-2021l-123/tbd-gatk:v0.1',
        image_pull_secrets=[k8s.V1LocalObjectReference('spark-jobs-sa-credentials')],
        cmds=["bash", "-cx", gatk_command],
        labels={"tbd": "variant_calling"},
        name="variant_calling_gatk",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="variant_calling",
        get_logs=True,
        env_vars=[k8s.V1EnvVar('SPARK_LOCAL_HOSTNAME', 'localhost')],
        image_pull_policy='Always'
    )

    annotation = SparkKubernetesOperator(
        task_id='annotation',
        namespace='default',
        kubernetes_conn_id="kubernetes_default",
        application_file="resources/seqtender/annotation.yaml",
        do_xcom_push=True,
        dag=dag
    )

    annotation_monitoring = SparkKubernetesSensor(
        task_id='annotation-monitoring',
        namespace="default",
        application_name="{{ task_instance.xcom_pull(task_ids='annotation')['metadata']['name'] }}",
        kubernetes_conn_id="kubernetes_default",
        dag=dag
    )

    alignment >> alignment_monitoring >> variant_calling >> annotation >> annotation_monitoring
    # alignment >> alignment_monitoring
    # variant_calling
    # annotation >> annotation_monitoring
