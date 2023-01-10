========
问题描述
========
监控虚拟机

解决方案
========

1. 通过libvirt配置channel, 把信息吐给宿主机生成log文件(通过配置文件控制是否生成对应的xml)
2. 在虚拟机启动telegraf, 采集相关信息
3. 通过宿主机的telegraf去生成对应的数据。

libvirt增加以下配置
===================

.. code::

    <channel type="file">
        <source path="/var/lib/nova/instances/370bc12f-2874-4334-9743-0caf4ac9da4b/monitor.log"/>
        <target type="virtio" name="org.monitor.0" state="connected"/>
        <alias name="channel1"/>
        <address type="virtio-serial" controller="0" bus="0" port="2"/>
    </channel>

虚拟机telegraf配置
==================

Linux

.. code::

    [global_tags]
      vm_os_type = "linux"
    [agent]
      interval = "120s"
      round_interval = true
      metric_batch_size = 1000
      metric_buffer_limit = 10000
      collection_jitter = "5s"
      flush_interval = "60s"
      flush_jitter = "10s"
      debug = false
      quiet = false
      hostname = ""
      omit_hostname = false
      logfile = "/var/log/telegraf/telegraf.log"
    [[outputs.file]]
      files = ["/dev/virtio-ports/org.monit.0"]
      data_format = "influx"
    [[inputs.disk]]
      ignore_fs = ["tmpfs", "devtmpfs", "devfs"]
    [[inputs.cpu]]
      percpu = false
      totalcpu = true
      fielddrop = ["time_*"]
    [[inputs.internal]]
    [[inputs.diskio]]
    [[inputs.kernel]]
    [[inputs.mem]]
    [[inputs.processes]]
    [[inputs.swap]]
    [[inputs.system]]
    [[inputs.net]]
    [[inputs.netstat]]
    {% if vgpu_avai %}
    [[inputs.nvidia_smi]]
      [processors.regex]]
        order = 10
        alias = 'nvidia_drop_pstate'
        namepass = ['nvidia_smi']
      [[processors.regex.tags]]
        key = 'pstate'
        pattern = 'P(\d)'
        replacement = '${1}'
      [[processors.converter]]
        order = 20
        alias = 'nvidia_drop_pstate'
        namepass = ['nvidia_smi']
      [processors.converter.tags]
        integer = ['pstate']
    {% endif %}

Windows

.. code::

    [agent]
      interval = "120s"
      round_interval = true
      metric_batch_size = 1000
      metric_buffer_limit = 10000
      flush_buffer_when_full = true
      collection_jitter = "5s"
      flush_interval = "60s"
      flush_jitter = "10s"
      debug = false
      quiet = false
      Hostname = ""
      logfile = "C:\\Program Files\\telegraf\\telegraf.log"
    [[outputs.file]]
      files = ["\\\\.\\Global\\org.qemu.monit_agent.0"]
      data_format = "influx"
    [[inputs.internal]]
    {% if vgpu_avai %}
    [[inputs.nvidia_smi]]
      bin_path = "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe"
      [processors.regex]]
        order = 10
        alias = 'nvidia_drop_pstate'
        namepass = ['nvidia_smi']
      [[processors.regex.tags]]
        key = 'pstate'
        pattern = 'P(\d)'
        replacement = '${1}'
      [[processors.converter]]
        order = 20
        alias = 'nvidia_drop_pstate'
        namepass = ['nvidia_smi']
      [processors.converter.tags]
        integer = ['pstate']
    {% endif %}
    [[inputs.win_perf_counters]]
    [[inputs.win_perf_counters.object]]
      ObjectName = "LogicalDisk"
      Instances = ["*"]
      Counters = ["% Idle Time","% Disk Time","% Disk Read Time","% Disk Write Time", "Current Disk Queue Length","% Free Space","Free Megabytes",]
      Measurement = "vm_win_disk"
    [[inputs.win_perf_counters.object]]
      ObjectName = "PhysicalDisk"
      Instances = ["*"]
      Counters = ["Disk Read Bytes/sec","Disk Write Bytes/sec","Current Disk Queue Length","Disk Reads/sec", "Disk Writes/sec","% Disk Time","% Disk Read Time","% Disk Write Time",]
      Measurement = "vm_win_diskio"
    [[inputs.win_perf_counters.object]]
      ObjectName = "Network Interface"
      Instances = ["*"]
      Counters = ["Bytes Received/sec","Bytes Sent/sec","Packets Received/sec","Packets Sent/sec", "Packets Received Discarded","Packets Outbound Discarded","Packets Received Errors","Packets Outbound Errors",]
      Measurement = "vm_win_net"
    [[inputs.win_perf_counters.object]]
      ObjectName = "Process"
      Instances = ["*"]
      Counters = ["% Processor Time","Handle Count","Private Bytes","Thread Count","Virtual Bytes","Working Set",]
      Measurement = "vm_win_proc"
    [[inputs.win_perf_counters.object]]
      ObjectName = "System"
      Instances = ["------"]
      Counters = ["Context Switches/sec","System Calls/sec","Processor Queue Length","System Up Time",]
      Measurement = "vm_win_system"


宿主机的telegraf配置
=====================

.. code::

    [agent]
      interval = "1s"
      round_interval = true
      metric_batch_size = 1000
      metric_buffer_limit = 10000
      collection_jitter = "5s"
      flush_interval = "60s"
      flush_jitter = "10s"
      debug = false
      quiet = false
      hostname = ""
      omit_hostname = false
    [[inputs.internal]]
    [[inputs.tail]]
        files = ["/var/lib/nova/instances/*/monitor.log"]
    [[outputs.prometheus_client]]
      listen = ":9273"
    [[inputs.exec]]
      commands = [
          "python /etc/nvidia_pci.py",
        ]
      timeout='5s'
      data_format="influx"
    [[processors.regex]]
      [[processors.regex.tags]]
        key = "path"
        pattern = ".*/(?P<uuid>[a-z0-9-]+)/monitor.log$"
        replacement = "${uuid}"
        result_key = "uuid"

nova需变动
===========

需要在libvirt里添加一个新的channel(参考: libvirt增加以下配置)

编辑 `/etc/kolla/nova-compute/nova.conf`, 增加以下配置

::
    [DEFAULT]
    enable_monitor_channel = 'yes'

如果值为'yes'或值为'auto',imagemeta里hw_monitor_guest_agent为True, 代表开启虚拟机监控,
如果值为'no', 代表关闭虚拟机监控

kolla-ansible需变动
====================

需要在计算节点增加telegraf容器(telegraf配置参考: 宿主机的telegraf配置)

运维
=====

需要定制包含telegraf的镜像(配置参考: 虚拟机telegraf配置, telegraf版本需大于1.11)
需要安装nvidia驱动