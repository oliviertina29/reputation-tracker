from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType,IntegerType, BooleanType
import logging
from datetime import datetime
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

def create_spark_connection():
    s_conn = None

    try:
        s_conn = SparkSession.builder \
            .master("spark://spark:7077") \
            .appName('SparkDataStreaming') \
            .getOrCreate()

        s_conn.sparkContext.setLogLevel("ERROR")
        logging.info("Spark connection created successfully!")
    except Exception as e:
        logging.error(f"Couldn't create the spark session due to exception {e}")

    return s_conn


def connect_to_kafka(spark_conn):
    spark_df = None
    try:
        spark_df = spark_conn.read \
            .format('kafka') \
            .option('kafka.bootstrap.servers', 'kafka:9092') \
            .option('encoding', 'UTF-8') \
            .option("delimiter", "\x01") \
            .option('subscribe', 'youtube') \
            .load()
        logging.info("kafka dataframe created successfully")
    except Exception as e:
        logging.warning(f"kafka dataframe could not be created because: {e}")

    return spark_df

def create_selection_df_from_kafka(spark_df):
    schema = StructType([
        StructField("author", StringType(), False),
        StructField("updated_at", StringType(), False),
        StructField("like_count", IntegerType(), False),
        StructField("text", StringType(), False),
         StructField("video_id", StringType(), False),
        StructField("public", BooleanType(), False),
    ])

    sel = spark_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col('value'), schema).alias('data')).select("data.*")
    print(sel)

    return sel

def write_data_in_hdfs(spark_df):
    current_date = datetime.now().strftime("%Y_%m_%d")
    current_time = datetime.now().strftime("%H_%M")

    parquet_path = f"hdfs://namenode:8020/hadoop/hdfs/youtube/{current_date}/data_{current_time}.parquet"

    spark_df.write.parquet(parquet_path)

def read_data_from_hdfs(spark_conn,date="2024_01_01",time="12_10"):
    # for LLM model and streamlit
    df = spark_conn.read.parquet(f"hdfs://namenode:8020/hadoop/hdfs/youtube/{date}/data_{time}.parquet")
    return df

if __name__ == "__main__":
    # create spark connection
    spark_conn = create_spark_connection()

    if spark_conn is not None:
        # connect to kafka with spark connection
        spark_df = connect_to_kafka(spark_conn)
        selection_df = create_selection_df_from_kafka(spark_df)

        write_data_in_hdfs(selection_df)

        df = read_data_from_hdfs(spark_conn)
        print("Let show data from HDFS")
        df.show()
