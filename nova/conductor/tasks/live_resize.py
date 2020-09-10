# Copyright 2018 Cloudbase Solutions Srl
# All Rights Reserved.
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

from nova.conductor.tasks import base
from nova.conductor.tasks import migrate
from nova import objects


class LiveResizeTask(base.TaskBase):

    def __init__(self, context, instance, flavor, image,
                 request_spec, query_client, compute_rpcapi):
        super(LiveResizeTask, self).__init__(context, instance)
        self.flavor = flavor
        self.image = image
        self.request_spec = request_spec
        self.query_client = query_client
        self.compute_rpcapi = compute_rpcapi
        self._migration = None
        self._source_cn = None
        self._held_allocations = None

    def _execute(self):
        migration = objects.Migration(context=self.context.elevated())
        migration.old_instance_type_id = self.instance.flavor.id
        migration.new_instance_type_id = self.flavor.id
        migration.status = 'pre-live-resize'
        migration.instance_uuid = self.instance.uuid
        migration.source_compute = self.instance.host
        migration.source_node = self.instance.node
        # TODO(rogeryu): Adds live-resize to the Migration model
        # migration_type Enum
        migration.migration_type = 'resize'
        migration.create()
        self._migration = migration

        self._source_cn, self._held_allocations = (
            migrate.replace_allocation_with_migration(
                self.context, self.instance, self._migration))

        self.query_client.select_destinations(
            self.context, self.request_spec, [self.instance.uuid],
            return_objects=True, return_alternates=True)

        self.compute_rpcapi.live_resize_instance(
            self.context, self.instance, self.image, self._migration,
            self.instance.node, self.flavor, self.instance.host)

    def rollback(self):
        if self._migration:
            self._migration.status = 'error'
            self._migration.save()

        if not self._held_allocations:
            return

        # NOTE(danms): We created new-style migration-based
        # allocations for the instance, but failed before we kicked
        # off the migration in the compute. Normally the latter would
        # do that cleanup but we never got that far, so do it here and
        # now.

        migrate.revert_allocation_for_migration(self.context, self._source_cn,
                                                self.instance, self._migration)
