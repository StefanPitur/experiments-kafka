We executed `sudo lshw -class network`, resulting in the following output:

```txt
  *-network:0
       description: Ethernet interface
       product: Ethernet Controller E810-C for QSFP
       vendor: Intel Corporation
       physical id: 0
       bus info: pci@0000:17:00.0
       logical name: enp23s0f0
       version: 02
       serial: 40:a6:b7:c3:3e:d0
       capacity: 25Gbit/s
       width: 64 bits
       clock: 33MHz
       capabilities: pm msi msix pciexpress vpd bus_master cap_list rom ethernet physical fibre 25000bt-fd autonegotiation
       configuration: autonegotiation=on broadcast=yes driver=ice driverversion=5.15.0-143-generic duplex=full firmware=4.51 0x8001e843 23.0.8 ip=192.168.0.101 latency=0 link=yes multicast=yes
       resources: irq:16 memory:98000000-99ffffff memory:9a010000-9a01ffff memory:9a100000-9a1fffff
  *-network:1 DISABLED
       description: Ethernet interface
       product: Ethernet Controller E810-C for QSFP
       vendor: Intel Corporation
       physical id: 0.1
       bus info: pci@0000:17:00.1
       logical name: enp23s0f1
       version: 02
       serial: 40:a6:b7:c3:3e:d1
       capacity: 25Gbit/s
       width: 64 bits
       clock: 33MHz
       capabilities: pm msi msix pciexpress vpd bus_master cap_list rom ethernet physical 10000bt-fd 25000bt-fd autonegotiation
       configuration: autonegotiation=off broadcast=yes driver=ice driverversion=5.15.0-143-generic firmware=4.51 0x8001e843 23.0.8 latency=0 link=no multicast=yes
       resources: irq:16 memory:96000000-97ffffff memory:9a000000-9a00ffff memory:9a200000-9a2fffff
  *-network:0
       description: Ethernet interface
       product: Ethernet Controller E810-XXV for SFP
       vendor: Intel Corporation
       physical id: 0
       bus info: pci@0000:6f:00.0
       logical name: eno12399
       version: 02
       serial: 30:3e:a7:1e:e1:74
       capacity: 25Gbit/s
       width: 64 bits
       clock: 33MHz
       capabilities: pm msi msix pciexpress vpd bus_master cap_list rom ethernet physical fibre 1000bt-fd 10000bt-fd 25000bt-fd autonegotiation
       configuration: autonegotiation=on broadcast=yes driver=ice driverversion=5.15.0-143-generic duplex=full firmware=4.51 0x8001e501 23.0.8 ip=128.110.220.112 latency=0 link=yes multicast=yes
       resources: irq:16 memory:c2000000-c3ffffff memory:c4010000-c401ffff memory:be800000-be8fffff
  *-network:1 DISABLED
       description: Ethernet interface
       product: Ethernet Controller E810-XXV for SFP
       vendor: Intel Corporation
       physical id: 0.1
       bus info: pci@0000:6f:00.1
       logical name: eno12409
       version: 02
       serial: 30:3e:a7:1e:e1:75
       capacity: 25Gbit/s
       width: 64 bits
       clock: 33MHz
       capabilities: pm msi msix pciexpress vpd bus_master cap_list rom ethernet physical fibre 1000bt-fd 10000bt-fd 25000bt-fd autonegotiation
       configuration: autonegotiation=off broadcast=yes driver=ice driverversion=5.15.0-143-generic firmware=4.51 0x8001e501 23.0.8 latency=0 link=no multicast=yes
       resources: irq:16 memory:c0000000-c1ffffff memory:c4000000-c400ffff memory:be900000-be9fffff
```

From which we conclude that for c6620 Utah hardware that we are using for the experiments,
- `enp23s0f0` is your Kafka workhorse:
    - 25GbE capacity (3.125 GB/s theoretical max).
    - Handles all broker/producer traffic (192.168.0.101).
    - Check: Confirm Kafka binds to this IP in server.properties.

- `eno12399` is for management:
    - Used for SSH/Grafana/Prometheus (128.110.220.112).
    - Ignore for throughput monitoring.

- No NIC bonding or redundancy:
    - Only `enp23s0f0` is active for data.

- All other interfaces (`enp23s0f1`, `eno12409`) are disabled.
