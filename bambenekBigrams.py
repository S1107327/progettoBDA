import os
from datasetWriter import dataset_writer
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from pyspark.sql import SQLContext
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.feature import NGram

# se è gia esistente prende lo SparkContext, oppure lo crea
sc = SparkContext.getOrCreate()
# crea una sessione nello spark Context in quanto ci possono essere più session
spark = SparkSession(sc)
# creazione dell'sqlContext per operare query SQL sui dataframe
sqlContext = SQLContext(sc)

def is_bigram(x):
    return BooleanType().toInternal(length(x) > 1)

# schema per la lettura dei dati dal feed bambenek
schema = StructType([
    StructField("domain", StringType(), True),
    StructField("description", StringType(), True),
    StructField("date", StringType(), True),
    StructField("link", StringType(), True),
])

# raccolta e ordinamento in una lista di tutti i nomi dei file del bambenek feed
bambenek_feeds = os.listdir(f"{os.environ['HOME']}/progettoBDA/DGAFeed/")
bambenek_feeds.sort()

# creazione di un dataframe vuoto per ospitare i dati provenienti dai nuovi feed di bambenek
evil_feed = spark.createDataFrame([],schema)

# Per ogni file da aggiungere si prendono i nomi e tutte le altre informazioni dal file eliminando le righe
# di intestazione. Dopodichè si estrae dalle informazioni associato al nome la famiglia a cui esso corrisponde
# mediante informazioni note e corrispondenze tra vari alias. Infine si ottiene  un dataframe che conterrà
# tutti i domini da aggiungere al feed complessivo di cui riportiamo nome e famiglia
for feed in bambenek_feeds:
    df = spark.read.format('csv').load(f"{os.environ['HOME']}/progettoBDA/DGAFeed/{feed}", schema=schema)
    evil_feed = evil_feed.union(df.filter(df['description'].isNotNull()))
evil_feed = evil_feed.withColumn("family", split(evil_feed['link'], '[/.]')[6])
evil_feed = evil_feed.withColumn("family", when(col('family') == 'cl', 'cryptolocker')
                                 .when(col('family') == 'wiki25', 'cryptolocker')
                                 .when(col('family') == 'bebloh', 'shiotob')
                                 .when(col('family') == 'ptgoz', 'zeus-newgoz').otherwise(col('family')))
evil_feed = evil_feed.select("family", "domain")

# si eliminano eventuali duplicati che esistono tra i file processati
evil_feed = evil_feed.dropDuplicates()

# si sostituisce la riga domain con noDotsDomains
evil_feed = evil_feed.select("family", split(concat_ws('', split("domain", '[.]')), '').alias("array_word"))
bigrams = NGram(n=2, inputCol="array_word", outputCol="bigrams")
evil_bigrams = bigrams.transform(evil_feed)
evil_bigrams = evil_bigrams.select("family",
                                    transform("bigrams",lambda x: concat_ws("", split(x, '[ ]'))).alias("bigrams"))
evil_bigrams = evil_bigrams.select("family",concat_ws(" ", filter("bigrams", is_bigram)).alias("bigrams"))
dataset_writer(f"{os.environ['HOME']}/progettoBDA/datasets/bambenekBigrams.csv", evil_bigrams, mode='w')