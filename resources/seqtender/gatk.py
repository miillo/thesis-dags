# check -> https://github.com/biodatageeks/ds-images/blob/main/ds-notebook/resources/edugen/bin/gatk-hpt-caller-k8s.sh
def generate_gatk_command(bucket, vcf_file, ref_file, bam_file, spark_master):
    return f"gatk HaplotypeCallerSpark \
      --spark-runner SPARK \
      --spark-master {spark_master} \
      --conf spark.jars=/tmp/gcs-connector-hadoop3-latest.jar \
      --conf spark.hadoop.google.cloud.auth.service.account.enable=true \
      --conf spark.executor.memory = 1g \
      --conf spark.driver.memory = 1g \
      --conf spark.executor.instances = 2 \
      --conf spark.hadoop.fs.gs.block.size = 8388608 \
      -R {ref_file} \
      -I {bucket}{bam_file} \
      -O {bucket}{vcf_file}"


# GATK with local spark execution: local[*]
def generate_gatk_local_command(bucket, vcf_file, ref_file, bam_file):
    return f"gatk HaplotypeCallerSpark \
      -R {ref_file} \
      -I {bucket}{bam_file} \
      -O {bucket}{vcf_file}"
