# Copyright (c) Intel Corporation.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from sqlalchemy import MetaData, Table, Column, Integer


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    compute_nodes = Table('compute_nodes', meta, autoload=True)
    shadow_compute_nodes = Table('shadow_compute_nodes', meta, autoload=True)

    total_vms = Column('total_vms', Integer)
    shadow_total_vms = Column('total_vms', Integer)

    if not hasattr(compute_nodes.c, 'total_vms'):
        compute_nodes.create_column(total_vms)
    if not hasattr(shadow_compute_nodes.c, 'total_vms'):
        shadow_compute_nodes.create_column(shadow_total_vms)
