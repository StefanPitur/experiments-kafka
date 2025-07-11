"""
This CloudLab profile sets up a configurable Apache Kafka cluster with optional producers and consumers.
It clones a custom Kafka fork from GitHub and prepares each node with monitoring and experimental datasets.

Instructions:

- Select the desired number of brokers, producers, and consumers when instantiating the experiment.
- Each node clones the Kafka codebase from: https://github.com/StefanPitur/kafka
- A Prometheus JMX exporter is downloaded and configured to monitor Kafka metrics on port 7071.
- A preloaded dataset is mounted at /experiments on every node.
- A logical volume is created and mounted at /mnt/kafka-data for Kafka logs and data.
- Environment variables for Kafka, Scala, and Gradle are exported via `.profile`.

Notes:
- Default image: c6620_kafka_codebase
- Hardware type: c6620
- All nodes are placed on a shared LAN with role-based static IPs.
- Kafka path: /users/pitur/kafka
- Kafka JMX configuration: /users/pitur/kafka/kafka-jmx.yml

This profile is suitable for performance testing, instrumentation, and real-world distributed system research.
"""

# type: ignore
import geni.portal as portal
import geni.rspec.pg as rspec

KAFKA_CLUSTER_ID = "imKy6K6KS-Serx1fhjChJg"
KAFKA_REPO = "https://github.com/StefanPitur/kafka.git"
KAFKA_PATH = "/users/pitur/kafka"
HARDWARE_TYPE = "c6620"
DATASET_URN = "urn:publicid:IDN+utah.cloudlab.us:isolateedinburgh-pg0+imdataset+kafka-experiment-configs"
DISK_IMAGE_URN = "urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:c6620_kafka_codebase"
ROLE_SUBNETS = {"broker": 1, "producer": 2, "consumer": 3}

# Create a Request object to start building the RSpec.
request = portal.context.makeRequestRSpec()

# Parameters
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
if params.BROKER_COUNT < 1:
    portal.context.reportError("There must be at least one broker", ["BROKER_COUNT"])
if params.PRODUCER_COUNT < 0:
    portal.context.reportError("Producer count cannot be negative", ["PRODUCER_COUNT"])
if params.CONSUMER_COUNT < 0:
    portal.context.reportError("Consumer count cannot be negative", ["CONSUMER_COUNT"])
portal.context.verifyParameters()

lan = request.LAN("lan")


# Create a node
def create_node(role, index):
    name = str(role) + "-" + str(index)
    ip = "192.168.0." + str(100 * ROLE_SUBNETS[role] + index)

    node = request.RawPC(name)
    node.hardware_type = HARDWARE_TYPE
    node.disk_image = DISK_IMAGE_URN
    node.routable_control_ip = True

    bs = node.Blockstore("bs-" + str(role) + "-" + str(index), "/experiments")
    bs.dataset = DATASET_URN

    iface = node.addInterface("if-" + str(role) + "-" + str(index))
    iface.addAddress(rspec.IPv4Address(ip, "255.255.255.0"))
    lan.addInterface(iface)

    clone_kafka(node)
    setup_profile_paths(node)


    node.addService(
        rspec.Execute(
            shell="bash",
            command="""
sudo lvcreate -l 100%FREE -n kafka-data emulab &&\
sudo mkfs.ext4 /dev/emulab/kafka-data &&\
sudo mkdir -p /mnt/kafka-data &&\
sudo mount /dev/emulab/kafka-data /mnt/kafka-data
""",
        )
    )

def clone_kafka(node):
    node.addService(
        rspec.Execute(
            shell="bash",
            command="""git clone {}""".format(KAFKA_REPO)
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="sudo wget https://github.com/prometheus/jmx_exporter/releases/download/1.3.0/jmx_prometheus_javaagent-1.3.0.jar -O {}/jmx_prometheus_javaagent.jar".format(KAFKA_PATH),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""cat <<EOF | sudo tee {}/kafka-jmx.yml > /dev/null
startDelaySeconds: 0
rules:
  - pattern: ".*"
EOF""".format(KAFKA_PATH),
        )
    )


def setup_profile_paths(node):
    node.addService(
        rspec.Execute(
            shell="bash",
            command="""echo 'export KAFKA_CLUSTER_ID={}' | sudo tee -a /users/pitur/.profile""".format(
                KAFKA_CLUSTER_ID
            ),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""echo 'export KAFKA_OPTS="-javaagent:{}/jmx_prometheus_javaagent.jar=7071:/opt/kafka/kafka-jmx.yml"' | sudo tee -a /users/pitur/.profile""".format(KAFKA_PATH),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""echo 'export PATH=$PATH:/opt/gradle/gradle-8.14.3/bin' | sudo tee -a /users/pitur/.profile"""
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""echo 'export PATH=/opt/scala/scala-2.13.13/bin:$PATH' | sudo tee -a /users/pitur/.profile"""
        )
    )

# Brokers
for i in range(params.BROKER_COUNT):
    create_node("broker", i + 1)

# Producers
for i in range(params.PRODUCER_COUNT):
    create_node("producer", i + 1)

# Consumers
for i in range(params.CONSUMER_COUNT):
    create_node("consumer", i + 1)

# Print the RSpec to the enclosing page.
portal.context.printRequestRSpec()
