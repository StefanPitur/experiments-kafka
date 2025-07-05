"""
CloudLab Kafka Testbed Profile

This profile launches a configurable number of Kafka brokers, producers, and consumers,
each running on separate bare-metal ARM or x86 nodes. Each role is connected to its own
subnet within a shared LAN - ideal for topologies testing or isolated networking.

Configuration:
- Brokers: Run Kafka cluster nodes.
- Producers and Consumers: Attach your load or test logic (to be mounted or started later).

Instructions:
1. Provide your custom disk image including Java, Kafka, and scripts via DISK_IMAGE_URN.
2. Optionally mount shared configuration files or datasets using DATASET_URN.
3. After provisioning, SSH into nodes to start your brokers or client processes:
   - Brokers: start-broker.sh (with JMX enabled).
   - Producers/Consumers: start scripts pointing to /experiments or configured paths.
4. Use CloudLab tools or SSH to simulate network faults or scale roles dynamically.

This base profile sets up hardware and storage; you can build experiments, attach configs,
or invoke role-specific automation on top in each node's local environment.
"""

# type: ignore
import geni.portal as portal
import geni.rspec.pg as rspec

KAFKA_CLUSTER_ID = "imKy6K6KS-Serx1fhjChJg"
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
portal.context.defineParameter(
    "HARDWARE_TYPE",
    "Type of hardware",
    portal.ParameterType.NODETYPE,
    "m400",
)
portal.context.defineParameter(
    name="DISK_IMAGE_URN",
    description="Disk image URN",
    typ=portal.ParameterType.IMAGE,
    defaultValue="urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:kafka-bare-metal",
    legalValues=[
        "urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:kafka-bare-metal",
        "urn:publicid:IDN+clemson.cloudlab.us+image+isolateedinburgh-PG0:c6420-kafka-bare-metal",
    ],
)
portal.context.defineParameter(
    name="DATASET_URN",
    description="Dataset URN",
    typ=portal.ParameterType.STRING,
    defaultValue="urn:publicid:IDN+utah.cloudlab.us:isolateedinburgh-pg0+imdataset+kafka-experiment-configs",
    legalValues=[
        "urn:publicid:IDN+utah.cloudlab.us:isolateedinburgh-pg0+imdataset+kafka-experiment-configs",
    ],
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
    ip = "192.168." + str(ROLE_SUBNETS[role]) + "." + str(index)

    node = request.RawPC(name)
    node.hardware_type = params.HARDWARE_TYPE
    node.disk_image = params.DISK_IMAGE_URN
    node.routable_control_ip = True

    if params.DATASET_URN:
        bs = node.Blockstore("bs-" + str(role) + "-" + str(index), "/experiments")
        bs.dataset = params.DATASET_URN

    iface = node.addInterface("if-" + str(role) + "-" + str(index))
    iface.addAddress(rspec.IPv4Address(ip, "255.255.255.0"))
    lan.addInterface(iface)

    node.addService(
        rspec.Execute(
            shell="bash",
            command="sudo wget https://github.com/prometheus/jmx_exporter/releases/download/1.3.0/jmx_prometheus_javaagent-1.3.0.jar -O /opt/kafka/jmx_prometheus_javaagent.jar",
        )
    )

    node.addService(
        rspec.Execute(
            shell="bash",
            command="""cat <<EOF | sudo tee /opt/kafka/kafka-jmx.yml > /dev/null
startDelaySeconds: 0
rules:
  - pattern: ".*"
EOF""",
        )
    )

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
            command="""echo 'export KAFKA_OPTS="-javaagent:/opt/kafka/jmx_prometheus_javaagent.jar=7071:/opt/kafka/kafka-jmx.yml"' | sudo tee -a /users/pitur/.profile""",
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
