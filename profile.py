"""This profile should spawn a configurable amount of brokers, producers and consumers,
each on a separate m400 RawPC. Currently, each category is executed on their own
individual LAN - could be adjusted in future profiles to simulate network partitions.

Instructions:
At the moment, it doesn't do much. I will add another parameter (say a path) to where
to load the configs from and start executing automatically. I think this could work for
brokers, maybe not so much for producers.
"""

# type: ignore
import geni.portal as portal
import geni.rspec.pg as rspec

HARDWARE_TYPE = "m400"
DISK_IMAGE_URN = (
    "urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:kafka-bare-metal"
)
DATASET_URN = "urn:publicid:IDN+utah.cloudlab.us:isolateedinburgh-pg0+imdataset+kafka-experiment-configs"
ROLE_SUBNETS = {"broker": 1, "producer": 2, "consumer": 3}
KAFKA_CLUSTER_ID = "imKy6K6KS-Serx1fhjChJg"

# Create a Request object to start building the RSpec.
request = portal.context.makeRequestRSpec()

# Parameters
portal.context.defineParameter(
    "EXPERIMENT_DIR",
    "Directory under /experiments where configs are",
    portal.ParameterType.STRING,
    "3_high_volume_ingest",
)
portal.context.defineParameter(
    "BROKER_COUNT", "Number of Kafka Brokers", portal.ParameterType.INTEGER, 3
)
portal.context.defineParameter(
    "PRODUCER_COUNT", "Number of Kafka Producers", portal.ParameterType.INTEGER, 1
)
portal.context.defineParameter(
    "CONSUMER_COUNT", "Number of Kafka Consumers", portal.ParameterType.INTEGER, 0
)
params = portal.context.bindParameters()

# Validation of parameters
if params.EXPERIMENT_DIR == "":
    portal.context.reportError(
        "Specify the directory of the experiment", ["EXPERIMENT_DIR"]
    )
if params.BROKER_COUNT < 1:
    portal.context.reportError("There must be at least one broker", ["BROKER_COUNT"])
if params.PRODUCER_COUNT < 0:
    portal.context.reportError("Producer count cannot be negative", ["PRODUCER_COUNT"])
if params.CONSUMER_COUNT < 0:
    portal.context.reportError("Consumer count cannot be negative", ["CONSUMER_COUNT"])
if params.PRODUCER_COUNT + params.CONSUMER_COUNT == 0:
    portal.context.reportError(
        "Can't run an experiment with no producers, nor consumers",
        ["PRODUCER_COUNT", "CONSUMER_COUNT"],
    )
portal.context.verifyParameters()

lan = request.LAN("lan")


# Create a node
def create_node(role, index, experiment_dir):
    name = str(role) + "-" + str(index)
    ip = "192.168." + str(ROLE_SUBNETS[role]) + "." + str(index)

    node = request.RawPC(name)
    node.hardware_type = HARDWARE_TYPE
    node.disk_image = DISK_IMAGE_URN

    bs = node.Blockstore("bs-" + str(role) + "-" + str(index), "/experiments")
    bs.dataset = DATASET_URN

    iface = node.addInterface("if-" + str(role) + "-" + str(index))
    iface.addAddress(rspec.IPv4Address(ip, "255.255.255.0"))
    lan.addInterface(iface)


# Brokers
for i in range(params.BROKER_COUNT):
    create_node("broker", i + 1, params.EXPERIMENT_DIR)

# Producers
for i in range(params.PRODUCER_COUNT):
    create_node("producer", i + 1, params.EXPERIMENT_DIR)

# Consumers
for i in range(params.CONSUMER_COUNT):
    create_node("consumer", i + 1, params.EXPERIMENT_DIR)

# Print the RSpec to the enclosing page.
portal.context.printRequestRSpec()
