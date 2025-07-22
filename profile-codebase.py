"""
This CloudLab profile provisions a configurable Apache Kafka cluster with optional producers and consumers,
using a custom Kafka fork along with system and JVM monitoring agents.

What It Sets Up:
- A user-defined number of Kafka **brokers**, **producers**, and **consumers**.
- All nodes run the `c6620_kafka_codebase` image on `c6620` hardware.
- Each node mounts the `kafka-experiment-configs` dataset at `/experiments`.
- A logical volume is created and mounted at `/mnt/kafka-data` to store Kafka logs and persistent data.

Kafka & Monitoring Environment:
- Clones a Kafka fork from: https://github.com/StefanPitur/kafka.git -> `/users/pitur/kafka`
- Sets up the Prometheus **JMX Exporter** for Kafka JVM metrics, listening on port **7071**
- Appends to `.profile` the necessary environment variables:
    - `KAFKA_CLUSTER_ID`
    - `KAFKA_OPTS` (includes the JMX agent)
    - Scala and Gradle paths
- **Node Exporter v1.9.1** is downloaded and started as a background process, listening on port **9100**
  for system-level metrics (CPU, memory, disk, etc.).

Progress Tracking:
- Execution progress is logged numerically (steps 0-7) to `/users/pitur/state.log`.
- This helps with debugging any boot-time or provisioning failures.

Networking:
- All nodes are connected to a shared LAN.
- Role-based static IPs:
    - Brokers: `192.168.0.1xx`
    - Producers: `192.168.0.2xx`
    - Consumers: `192.168.0.3xx`

Parameters:
- `BROKER_COUNT` (default: 3): Number of Kafka broker nodes
- `PRODUCER_COUNT` (default: 1): Number of Kafka producer nodes
- `CONSUMER_COUNT` (default: 0): Number of Kafka consumer nodes

Use Cases:
- Kafka performance & stress testing
- Monitoring with Prometheus (JMX + Node Exporter)
- JVM instrumentation and system resource tracking
- Distributed systems benchmarking and protocol experimentation
"""

# type: ignore
import geni.portal as portal
import geni.rspec.pg as rspec

PWD = "/users/pitur"
KAFKA_CLUSTER_ID = "imKy6K6KS-Serx1fhjChJg"
KAFKA_REPO = "https://github.com/StefanPitur/kafka.git"
KAFKA_PATH = PWD + "/kafka"
HARDWARE_TYPE = "c6620"
DATASET_URN = "urn:publicid:IDN+utah.cloudlab.us:isolateedinburgh-pg0+imdataset+kafka-experiment-configs"
DISK_IMAGE_URN = (
    "urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:c6620_kafka_codebase"
)
ROLE_SUBNETS = {"broker": 1, "producer": 2, "consumer": 0}

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

    clone_kafka(node)
    setup_profile_paths(node)
    start_node_exporter(node)


def clone_kafka(node):
    node.addService(
        rspec.Execute(
            shell="bash",
            command="""sudo -u pitur git clone {} {}""".format(KAFKA_REPO, KAFKA_PATH),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="sudo wget https://github.com/prometheus/jmx_exporter/releases/download/1.3.0/jmx_prometheus_javaagent-1.3.0.jar -O {}/jmx_prometheus_javaagent.jar".format(
                KAFKA_PATH
            ),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""cat <<EOF | sudo tee {}/kafka-jmx.yml > /dev/null
startDelaySeconds: 0
rules:
  - pattern: ".*"
EOF""".format(
                KAFKA_PATH
            ),
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
            command="""echo 'export KAFKA_OPTS="-javaagent:{}/jmx_prometheus_javaagent.jar=7071:{}/kafka-jmx.yml"' | sudo tee -a /users/pitur/.profile""".format(
                KAFKA_PATH, KAFKA_PATH
            ),
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""echo 'export PATH=$PATH:/opt/gradle/gradle-8.14.3/bin:/opt/scala/scala-2.13.13/bin' | sudo tee -a /users/pitur/.profile""",
        )
    )


def start_node_exporter(node):
    node.addService(
        rspec.Execute(
            shell="bash",
            command="""
cd {} && \
sudo wget https://github.com/prometheus/node_exporter/releases/download/v1.9.1/node_exporter-1.9.1.linux-amd64.tar.gz && \
sudo tar -xzf node_exporter-1.9.1.linux-amd64.tar.gz && \
sudo rm node_exporter-1.9.1.linux-amd64.tar.gz && \
sudo -u pitur nohup /{}/node_exporter-1.9.1.linux-amd64/node_exporter \
  --collector.diskstats \
  --collector.netdev \
  --web.listen-address=":9100" \
  > /tmp/node_exporter.log 2>&1 &
""".format(
                PWD, PWD
            ),
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
