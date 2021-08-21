import shutil
import fileinput
from csv import DictReader
import uuid

push_gateway_address = "10.28.6.236:9091"
config_filepath = 'resources/dag_config/dag_config.csv'
dag_template_filename = 'ngs_pipeline_template.py'
alignment_template_filename = 'resources/seqtender/alignment_template.yaml'
annotation_template_filename = 'resources/seqtender/annotation_template.yaml'
uuids = []


def main():
    with open(config_filepath, newline='') as csvfile:
        reader = DictReader(csvfile)
        for row in reader:  # each row is a new DAG/config file
            unique_dag_uuid = uuid.uuid4()
            new_dag_filename = 'ngs_pipeline_' + str(unique_dag_uuid) + '.py'
            new_alignment_config_filename = 'resources/seqtender/' + 'alignment-' + str(unique_dag_uuid) + '.yaml'
            new_annotation_config_filename = 'resources/seqtender/' + 'annotation-' + str(unique_dag_uuid) + '.yaml'
            shutil.copyfile(dag_template_filename, new_dag_filename)
            shutil.copyfile(alignment_template_filename, new_alignment_config_filename)
            shutil.copyfile(annotation_template_filename, new_annotation_config_filename)

            for line in fileinput.input(new_alignment_config_filename, inplace=True):
                line = line.replace("{dag_run_uuid}", str(unique_dag_uuid).split('-')[0])
                line = line.replace("{push_gateway_address}", push_gateway_address)
                line = line.replace("{executor_instances}", str(row.get("executor_instances")))
                line = line.replace("{executor_memory}", str(row.get("executor_memory")))
                line = line.replace("{driver_memory}", str(row.get("driver_memory")))
                print(line, end='')

            for line in fileinput.input(new_annotation_config_filename, inplace=True):
                line = line.replace("{dag_run_uuid}", str(unique_dag_uuid).split('-')[0])
                line = line.replace("{push_gateway_address}", push_gateway_address)
                line = line.replace("{executor_instances}", str(row.get("executor_instances")))
                line = line.replace("{executor_memory}", str(row.get("executor_memory")))
                line = line.replace("{driver_memory}", str(row.get("driver_memory")))
                print(line, end='')

            for line in fileinput.input(new_dag_filename, inplace=True):
                line = line.replace("{dag_run_uuid}", str(unique_dag_uuid))
                line = line.replace("{push_gateway_address}", push_gateway_address)
                line = line.replace("{dag_id}", "ngs-pipeline-" + str(unique_dag_uuid))
                line = line.replace("{parameters}", str(list(row.keys())))

                params_with_values = {k: k + '="' + v + '"' for k, v in row.items()}
                params_list = list(params_with_values.values())
                line = line.replace("{parameters_with_values}", ",".join(params_list))

                line = line.replace("{alignment_spark_config}", "alignment-" + str(unique_dag_uuid))
                line = line.replace("{annotation_spark_config}", "annotation-" + str(unique_dag_uuid))
                print(line, end='')

            uuids.append(str(unique_dag_uuid))

    return uuids


result_uuids = main()
print(result_uuids)
with open('result_uuids.txt', mode="wt") as myfile:
    myfile.write("\n".join(result_uuids))
