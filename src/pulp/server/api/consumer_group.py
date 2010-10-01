#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging

from pulp.server.agent import Agent
from pulp.server.api.base import BaseApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.pexceptions import PulpException
from pulp.server.async import AsyncAgent, AgentTask

log = logging.getLogger(__name__)


class ConsumerGroupApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.consumerApi = ConsumerApi()
        self.repoApi = RepoApi()
        
    @property
    def _unique_indexes(self):
        return ["id"]

    @property
    def _indexes(self):
        return ["consumerids"]    

    def _getcollection(self):
        return get_object_db('consumergroups',
                             self._unique_indexes,
                             self._indexes)


    @audit(params=['id', 'consumerids'])
    def create(self, id, description, consumerids=()):
        """
        Create a new ConsumerGroup object and return it
        """
        consumergroup = self.consumergroup(id)
        if(consumergroup):
            raise PulpException("A Consumer Group with id %s already exists" % id)
        
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            if (consumer is None):
                raise PulpException("No Consumer with id: %s found" % consumerid)
                
        c = model.ConsumerGroup(id, description, consumerids)
        self.insert(c)
        return c


    def consumergroups(self, spec=None, fields=None):
        """
        List all consumer groups.
        """
        return list(self.objectdb.find(spec=spec, fields=fields))   

    def consumergroup(self, id):
        """
        Return a single ConsumerGroup object
        """
        return self.objectdb.find_one({'id': id})


    def consumers(self, id):
        """
        Return consumer ids belonging to this ConsumerGroup
        """
        consumer = self.objectdb.find_one({'id': id})
        return consumer['consumerids']


    @audit()
    def add_consumer(self, groupid, consumerid):
        """
        Adds the passed in consumer to this group
        """
        consumergroup = self.consumergroup(groupid)
        if (consumergroup is None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumer = self.consumerApi.consumer(consumerid)
        if (consumer is None):
            raise PulpException("No Consumer with id: %s found" % consumerid)
        self._add_consumer(consumergroup, consumer)
        self.update(consumergroup)

    def _add_consumer(self, consumergroup, consumer):
        """
        Responsible for properly associating a Consumer to a ConsumerGroup
        """
        consumerids = consumergroup['consumerids']
        if consumer["id"] in consumerids:
            return
        
        consumerids.append(consumer["id"])
        consumergroup["consumerids"] = consumerids

    @audit()
    def delete_consumer(self, groupid, consumerid):
        consumergroup = self.consumergroup(groupid)
        if (consumergroup is None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumerids = consumergroup['consumerids']
        if consumerid not in consumerids:
            return
        consumerids.remove(consumerid)
        consumergroup["consumerids"] = consumerids
        self.update(consumergroup)

    @audit()
    def bind(self, id, repoid):
        """
        Bind (subscribe) a consumer group to a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to bind.
        @type repoid: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        repo = self.repoApi.repository(repoid)
        if repo is None:
            raise PulpException("No Repository with id: %s found" % repoid)

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.bind(consumerid, repoid)

    @audit()
    def unbind(self, id, repoid):
        """
        Unbind (unsubscribe) a consumer group from a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to unbind.
        @type repoid: str
        @raise PulpException: When consumer group not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        repo = self.repoApi.repository(repoid)
        if (repo is None):
            raise PulpException("No Repository with id: %s found" % repoid)

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.unbind(consumerid, repoid)

    def find_consumers_with_conflicting_keyvalues(self, id, key, value):
        """
        Find consumers belonging to this consumer group with conflicting key-values.
        """
        conflicting_consumers = []
        consumergroup = self.consumergroup(id)
        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            consumer_keyvalues = consumer['key_value_pairs']
            if key in consumer_keyvalues.keys() and consumer_keyvalues[key]!=value:
                conflicting_consumers.append(consumerid) 
        return conflicting_consumers


    @audit()
    def add_key_value_pair(self, id, key, value):
        """
        Add key-value info to a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)    
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)
        
        key_value_pairs = consumergroup['key_value_pairs']
        if key not in key_value_pairs.keys():
            conflicting_consumers = self.find_consumers_with_conflicting_keyvalues(id, key, value)
            if conflicting_consumers is []:
                key_value_pairs[key] = value
            else:    
                raise PulpException('Given key [%s] has different values for consumers [%s] '
                                    'belonging to this group. You can use --force to '
                                    'delete consumers\' original values.', key, conflicting_consumers)             
        else: 
            raise PulpException('Given key [%s] already exists', key)    
        consumergroup['key_value_pairs'] = key_value_pairs
        self.update(consumergroup)   
            
                        
    @audit()
    def delete_key_value_pair(self, id, key):
        """
        delete key-value info from a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)    
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)
        
        key_value_pairs = consumergroup['key_value_pairs']
        if key in key_value_pairs.keys():
            del key_value_pairs[key] 
        else: 
            raise PulpException('Given key [%s] does not exist', key)
        consumergroup['key_value_pairs'] = key_value_pairs
        self.update(consumergroup)

    @audit()
    def update_key_value_pair(self, id, key, value):
        """
        Update key-value info of a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)    
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)
        
        key_value_pairs = consumergroup['key_value_pairs']
        if key not in key_value_pairs.keys():
            raise PulpException('Given key [%s] does not exist', key)    
        else: 
            conflicting_consumers = self.find_consumers_with_conflicting_keyvalues(id, key, value)
            if conflicting_consumers is []:
                key_value_pairs[key] = value
            else:    
                raise PulpException('Given key [%s] has different values for consumers [%s] '
                                    'belonging to this group. You can use --force to '
                                    'delete consumers\' original values.', key, conflicting_consumers)             

        consumergroup['key_value_pairs'] = key_value_pairs
        self.update(consumergroup)
                
        
    @audit()
    def installpackages(self, id, packagenames=[]):
        """
        Install packages on the consumers in a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:   
            raise PulpException("No Consumer Group with id: %s found" % id)
        items = []
        for consumerid in consumergroup['consumerids']:
            items.append((consumerid, packagenames))
        task = InstallPackages(items)
    
    def installerrata(self, id, errataids=[], types=[]):
        """
        Install errata on a consumer group.
        @param id: A consumergroup id.
        @type id: str
        @param errataids: The errata ids to install.
        @type errataids: [str,..]
        @param types: Errata type filter
        @type types: str
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:   
            raise PulpException("No Consumer Group with id: %s found" % id)
        consumerids = consumergroup['consumerids']
        items = []
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            pkgs = []
            if errataids:
                applicable_errata = self.consumerApi._applicable_errata(consumer, types)
                for eid in errataids:
                    for pobj in applicable_errata[eid]:
                        if pobj["arch"] != "src":
                            pkgs.append(pobj["name"]) # + "." + pobj["arch"])
            else:
                #apply all updates
                pkgobjs = self.consumerApi.list_package_updates(id, types)
                for pobj in pkgobjs:
                    if pobj["arch"] != "src":
                        pkgs.append(pobj["name"]) # + "." + pobj["arch"])
            log.error("Foe consumer id %s Packages to install %s" % (consumerid, pkgs))
            items.append((consumerid, pkgs))
        task = InstallErrata(items)
        return task


class InstallPackages(AgentTask):
    """
    Install packages task
    @ivar items: The list of tuples (consumerid, [package,..]).
    @type items: list]
    @ivar serials: A dict of RMI serial # to consumer ids.
    @type serials: dict.
    @ivar __succeeded: A list of succeeded RMI.
    @type __succeeded: tuple (consumerid, result)
    @ivar __failed: A list of failed RMI.
    @type __failed: tuple (consumerid, exception)
    """

    def __init__(self, items, errata=()):
        """
        @param items: The list of tuples (consumerid, [package,..]).
        @type items: list
        @param errata: A list of errata titles.
        @type errata: list
        """
        self.items = items
        self.errata = errata
        self.serials = {}
        self.__succeeded = []
        self.__failed = []
        AgentTask.__init__(self, self.install)
        self.enqueue()

    def install(self):
        """
        Perform the RMI to the agent to install packages.
        """
        for id, pkglist in self.items:
            agent = AsyncAgent(id)
            packages = agent.Packages(self)
            sn = packages.install(pkglist)
            self.serials[sn] = id

    def succeeded(self, sn, result):
        """
        The agent RMI Succeeded.
        Find the consumer id using the serial number.  Then, append the
        result to the succeeded list and check to see if we have all
        of the replies (finished).
        @param sn: The RMI serial #.
        @type sn: uuid
        @param result: The object returned by the RMI call.
        @type result: object
        """
        id = self.serials.get(sn)
        if not id:
            log.error('serial %s, not found', sn)
            return
        self.__succeeded.append((id, result))
        self.__finished()

    def failed(self, sn, exception, tb=None):
        """
        The agent RMI Failed.
        Find the consumer id using the serial number.  Then, append the
        exception and traceback to the failed list and check to see if
        we have all of the replies (finished).
        @param sn: The RMI serial #.
        @type sn: uuid
        @param exception: The I{representation} of the raised exception.
        @type exception: str
        @param tb: The formatted traceback.
        @type tb: str
        """
        id = self.serials.get(sn)
        if not id:
            log.error('serial %s, not found', sn)
            return
        self.__failed.append((id, exception, tb))
        self.__finished()

    def __finished(self):
        """
        See if were finished.
        @param reply: An RMI reply object.
        @type reply: Reply
        """
        total = len(self.serials)
        total -= len(self.__succeeded)
        total -= len(self.__failed)
        if total: # still have outstanding replies
            return
        result = (self.__succeeded, self.__failed)
        AgentTask.succeeded(self, None, result)
        chapi = ConsumerHistoryApi()
        for id, result in self.__succeeded:
            chapi.packages_installed(
                    id,
                    result,
                    errata_titles=self.errata)


class InstallErrata(InstallPackages):
    """
    Install errata task.
    """
    pass
