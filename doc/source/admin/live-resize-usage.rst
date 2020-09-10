==================
虚拟机在线修改配置
==================

功能描述
========

虚拟机在线修改配置功能允许用户在线添加虚拟机的CPU与内存资源。
配置修改完成后，用户不需要重启虚拟机，配置立即生效。用户若想
使用该功能，需要在创建该虚拟机时指定允许其拥有的最大CPU/内存
数量。用户可对同一虚拟机进行多次在线修改配置，但CPU/内存数量
不能超过创建时指定的最大CPU/内存数量。CPU/内存均只能在线增加
或扩展，不能在线减少或缩小。

使用场景
========

在线增加CPU/内存
----------------

随着业务规模的不断增长，当用户发现虚拟机CPU/内存资源无法满足
现有业务需求时，需要增加虚拟机的CPU与内存资源。以往的版本中，
云平台不具备在线增加CPU/内存的能力，用户在此场景下，修改虚拟
机配置需要重启虚拟机，造成业务中断，用户体验不够友好。因此，
在线增加CPU/内存的功能，使用户能够更加灵活的修改虚拟机配置，
从而完成业务的扩展。


变更项目
========

Nova:

* 新增API: live-resize, 该API可对虚拟机在线增加CPU/内存
* 在libvirt driver中实现live-resize的业务逻辑
* 为虚拟机增加一种任务状态: live-resizing

python-novaclient:

* server新增live-resize功能

设计思路
--------

* live-resize包括在线添加CPU与内存。其中在线添加CPU与内存使
  用新的Nova API接口
* 在线添加CPU与内存的实现中，需要用户在创建虚拟机的时候指定
  是否使用在线升级，同时可以指定虚拟机允许拥有的最大CPU与内存
  数量。这三个参数通过虚拟机的flavor传入，分别是'hw:live_resize'、
  'hw:live_resize_max_vcpus'与'hw:live_resize_max_memory'，在
  libvirt driver中将其设置在虚拟机的配置信息中
* 虚拟机的max_vcpus与max_memory在启动时设置完成之后，不能修改，
  因此无法在虚拟机启动完成后修改其允许拥有的最大CPU与内存数量
* 虚拟机可以单独添加CPU或者内存数量，无需两者一同添加

依赖
====

* 在线修改配置仅针对libvirt做实现，其他类型的Hypervisor尚不
  支持

特殊说明
========
1. flavor中'hw:live_resize_max_vcpus'与'hw:live_resize_max_memory'
   未配置时，默认值将使用当前计算节点cpu、memory的一半
2. 内存在线扩容时，内存增量(new_flavor_mem - old_flavor_mem)应设置
   为128M的整数倍(操作系统底层要求)
3. 由于内存热扩容必须配置guest os numa信息，必须为使用的flavor添加
   hw:numa_nodes参数
4. 计算节点具有双路cpu，当flavor的vcpu > 1时，hw:numa_nodes=2;
   flavor的vcpu = 1时，hw:numa_nodes=1;
   其余情况作适当调整
5. 虚拟机热升级后，若无法发现新增内存，可能是由于虚拟机的
   CONFIG_MEMORY_HOTPLUG该内核参数未使能，该参数用于控制热插拔内存
   是否直接生效，enable新增内存的具体方法参考测试用例4；
   虚拟机操作系统建议使用CentOS7，3.10之后的linux内核版本该参数都默
   认生效

测试用例
========
1. 创建flavor::

    # openstack flavor create --ram 50 --vcpus 1 --disk 1 --property hw:live_resize=True --property hw:numa_nodes=1 lr.1
    +----------------------------+------------------------------------------+
    | Field                      | Value                                    |
    +----------------------------+------------------------------------------+
    | OS-FLV-DISABLED:disabled   | False                                    |
    | OS-FLV-EXT-DATA:ephemeral  | 0                                        |
    | disk                       | 1                                        |
    | id                         | 0c1e5918-bbc0-41ed-96c1-03a82dc2c3d0     |
    | name                       | lr.1                                     |
    | os-flavor-access:is_public | True                                     |
    | properties                 | hw:live_resize='True', hw:numa_nodes='1' |
    | ram                        | 50                                       |
    | rxtx_factor                | 1.0                                      |
    | swap                       |                                          |
    | vcpus                      | 1                                        |
    +----------------------------+------------------------------------------+
    # openstack flavor create --ram 178 --vcpus 2 --disk 1 --property hw:live_resize=True --property hw:numa_nodes=1 lr.2
    +----------------------------+------------------------------------------+
    | Field                      | Value                                    |
    +----------------------------+------------------------------------------+
    | OS-FLV-DISABLED:disabled   | False                                    |
    | OS-FLV-EXT-DATA:ephemeral  | 0                                        |
    | disk                       | 1                                        |
    | id                         | 8289d5dc-186e-4ba4-9c49-eba0a4fca3ed     |
    | name                       | lr.2                                     |
    | os-flavor-access:is_public | True                                     |
    | properties                 | hw:live_resize='True', hw:numa_nodes='1' |
    | ram                        | 178                                      |
    | rxtx_factor                | 1.0                                      |
    | swap                       |                                          |
    | vcpus                      | 2                                        |
    +----------------------------+------------------------------------------+

2. 创建server::

    # openstack server create --flavor lr.1 --network test --image cirros live_resize_test_1
    +-------------------------------------+-----------------------------------------------+
    | Field                               | Value                                         |
    +-------------------------------------+-----------------------------------------------+
    | OS-DCF:diskConfig                   | MANUAL                                        |
    | OS-EXT-AZ:availability_zone         |                                               |
    | OS-EXT-SRV-ATTR:host                | None                                          |
    | OS-EXT-SRV-ATTR:hypervisor_hostname | None                                          |
    | OS-EXT-SRV-ATTR:instance_name       |                                               |
    | OS-EXT-STS:power_state              | NOSTATE                                       |
    | OS-EXT-STS:task_state               | scheduling                                    |
    | OS-EXT-STS:vm_state                 | building                                      |
    | OS-SRV-USG:launched_at              | None                                          |
    | OS-SRV-USG:terminated_at            | None                                          |
    | accessIPv4                          |                                               |
    | accessIPv6                          |                                               |
    | addresses                           |                                               |
    | adminPass                           | yszi6jsyBC9W                                  |
    | config_drive                        |                                               |
    | created                             | 2020-09-14T13:13:00Z                          |
    | flavor                              | lr.1 (0c1e5918-bbc0-41ed-96c1-03a82dc2c3d0)   |
    | hostId                              |                                               |
    | id                                  | b85b2bd5-a545-4ebf-bc5b-3bfff74002e1          |
    | image                               | cirros (2da9cda7-d14a-4e91-bb65-484906f6eb54) |
    | key_name                            | None                                          |
    | name                                | live_resize_test_1                            |
    | progress                            | 0                                             |
    | project_id                          | 4d04c51c4122468489bda615856ef503              |
    | properties                          |                                               |
    | security_groups                     | name='default'                                |
    | status                              | BUILD                                         |
    | updated                             | 2020-09-14T13:13:00Z                          |
    | user_id                             | 6d9c1661dfdc4620ac38760b701b8c86              |
    | volumes_attached                    |                                               |
    +-------------------------------------+-----------------------------------------------+

3. 热升级server::

    # nova live-resize live_resize_test_1 lr.2
    # openstack server show live_resize_test_1
    +-------------------------------------+----------------------------------------------------------+
    | Field                               | Value                                                    |
    +-------------------------------------+----------------------------------------------------------+
    | OS-DCF:diskConfig                   | MANUAL                                                   |
    | OS-EXT-AZ:availability_zone         | nova                                                     |
    | OS-EXT-SRV-ATTR:host                | localhost.localdomain                                    |
    | OS-EXT-SRV-ATTR:hypervisor_hostname | localhost.localdomain                                    |
    | OS-EXT-SRV-ATTR:instance_name       | instance-0000004d                                        |
    | OS-EXT-STS:power_state              | Running                                                  |
    | OS-EXT-STS:task_state               | None                                                     |
    | OS-EXT-STS:vm_state                 | active                                                   |
    | OS-SRV-USG:launched_at              | 2020-09-14T13:13:07.000000                               |
    | OS-SRV-USG:terminated_at            | None                                                     |
    | accessIPv4                          |                                                          |
    | accessIPv6                          |                                                          |
    | addresses                           | test=192.168.111.164                                     |
    | config_drive                        |                                                          |
    | created                             | 2020-09-14T13:13:00Z                                     |
    | flavor                              | lr.2 (8289d5dc-186e-4ba4-9c49-eba0a4fca3ed)              |
    | hostId                              | b755d36b25a9a78b0f383d413cddb19e7bfab40c413d628da2f950e9 |
    | id                                  | b85b2bd5-a545-4ebf-bc5b-3bfff74002e1                     |
    | image                               | cirros (2da9cda7-d14a-4e91-bb65-484906f6eb54)            |
    | key_name                            | None                                                     |
    | name                                | live_resize_test_1                                       |
    | progress                            | 0                                                        |
    | project_id                          | 4d04c51c4122468489bda615856ef503                         |
    | properties                          |                                                          |
    | security_groups                     | name='default'                                           |
    | status                              | ACTIVE                                                   |
    | updated                             | 2020-09-14T13:17:26Z                                     |
    | user_id                             | 6d9c1661dfdc4620ac38760b701b8c86                         |
    | volumes_attached                    |                                                          |
    +-------------------------------------+----------------------------------------------------------+

4. 登录控制台进行检验::

    # 查看CPU
    $ lscpu | grep CPU\(s\)
    CPU(s):              2
    # 查看内存
    $ free -m
                  total        used        free      shared    buffers
    Mem:             32          25           6           0          2
    -/+ buffers                  23           8
    Swap:             0           0           0
    # 查看新增内存块状态
    $ ls /sys/devices/system/memory/ |grep memory
    memory0
    memory32
    $ cat /sys/devices/system/memory/memory32/state
    offline
    # 使能(还可以编辑/sys/devices/system/memory/memory32/online的值为1)
    $ echo online > /sys/devices/system/memory/memory32/state
    # 再次查看内存
                  total        used        free      shared    buffers
    Mem:            160          26         134           0          2
    -/+ buffers                  23         136
    Swap:             0           0           0

    注意：CONFIG_MEMORY_HOTPLUG该内核参数控制热插拔内存是否直接生效，查看方式：
        cat /boot/config-/boot/config-`uname -r` | grep
