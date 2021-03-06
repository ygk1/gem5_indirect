# Copyright (c) 2012-2013, 2015-2016 ARM Limited
# Copyright (c) 2020 Barkhausen Institut
# All rights reserved
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2010 Advanced Micro Devices, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Configure the M5 cache hierarchy config in one place
#

import m5
from m5.objects import *
from common.Caches import *
from common import ObjectList

def _get_hwp(hwp_option):
    if hwp_option == None:
        return NULL

    hwpClass = ObjectList.hwp_list.get(hwp_option)
    return hwpClass()

def _get_cache_opts(level, options):
    opts = {}

    size_attr = '{}_size'.format(level)
    if hasattr(options, size_attr):
        opts['size'] = getattr(options, size_attr)

    assoc_attr = '{}_assoc'.format(level)
    if hasattr(options, assoc_attr):
        opts['assoc'] = getattr(options, assoc_attr)

    prefetcher_attr = '{}_hwp_type'.format(level)
    if hasattr(options, prefetcher_attr):
        opts['prefetcher'] = _get_hwp(getattr(options, prefetcher_attr))

    return opts

def config_cache(options, system):
    if options.external_memory_system and (options.caches or options.l2cache):
        print("External caches and internal caches are exclusive options.\n")
        sys.exit(1)

    if options.external_memory_system:
        ExternalCache = ExternalCacheFactory(options.external_memory_system)

    if options.cpu_type == "O3_ARM_v7a_3":
        try:
            import cores.arm.O3_ARM_v7a as core
        except:
            print("O3_ARM_v7a_3 is unavailable. Did you compile the O3 model?")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = \
            core.O3_ARM_v7a_DCache, core.O3_ARM_v7a_ICache, \
            core.O3_ARM_v7aL2, \
            core.O3_ARM_v7aWalkCache
    elif options.cpu_type == "HPI":
        try:
            import cores.arm.HPI as core
        except:
            print("HPI is unavailable.")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = \
            core.HPI_DCache, core.HPI_ICache, core.HPI_L2, core.HPI_WalkCache
    else:
        dcache_class, icache_class, l2_cache_class, l3_cache_class, walk_cache_class = \
            L1_DCache, L1_ICache, L2Cache, L3Cache, None

        if buildEnv['TARGET_ISA'] in ['x86', 'riscv']:
            walk_cache_class = PageTableWalkerCache

    # Set the cache line size of the system
    system.cache_line_size = options.cacheline_size

    # If elastic trace generation is enabled, make sure the memory system is
    # minimal so that compute delays do not include memory access latencies.
    # Configure the compulsory L1 caches for the O3CPU, do not configure
    # any more caches.
    if options.l2cache and options.elastic_trace_en:
        fatal("When elastic trace is enabled, do not configure L2 caches.")

    
    if options.l3cache and options.l2cache:
        # Provide a clock for the L2 and the L1-to-L2 bus here as they
        # are not connected using addTwoLevelCacheHierarchy. Use the
        # same clock as the CPUs.
        system.l3 = l3_cache_class(clk_domain=system.cpu_clk_domain,
                                   **_get_cache_opts('l3', options))
        system.tol3bus = L3XBar(clk_domain = system.cpu_clk_domain)
       
        system.l3.cpu_side = system.tol3bus.master
        system.l3.mem_side = system.membus.slave
        l3latency = 54
        if options.mirage_mode_l3:
            if options.mirage_mode_l3 == "Baseline":
                system.l3.tag_latency     = l3latency
            elif options.mirage_mode_l3 == "BaselineRRIP":
                system.l3.tag_latency     = l3latency
                system.l3.replacement_policy = RRIPRP()
            elif options.mirage_mode_l3 == "BaselineBRRIP":
                system.l3.tag_latency     = l3latency
                system.l3.replacement_policy = BRRIPRP()
                system.l3.replacement_policy.btp = 5;
            elif options.mirage_mode_l3 == "scatter-cache":
                system.l3.skewedCache = True
                system.l3.randomizedIndexing = True
            elif options.mirage_mode_l3 == "vway-rand":
                system.l3.vwayCache = True
                system.l3.randomizedIndexing = True
            elif ((options.mirage_mode_l3 == "skew-vway-rand") or (options.mirage_mode_l3 == "skew-vway-rand-datareuserepl")):
                system.l3.vwayCache = True
                system.l3.randomizedIndexing = True
                system.l3.skewedCache = True
            elif options.mirage_mode_l3 == "cuckoo-skew-vway-rand":
                system.l3.vwayCache = True
                system.l3.randomizedIndexing = True
                system.l3.skewedCache = True
                system.l3.p2_on_conflict = True
                system.l3.cuckoo_on_conflict = True
            elif options.mirage_mode_l3 == "skew-vway-indirect":
                system.l3.indirectCache = True
                system.l3.randomizedIndirectIndexing = True
                system.l3.skewedCache = True
            else:
                fatal("Used a mirage_mode that is not supported")
            if (str(system.l3.indirectCache) == "True"):
                assert str(system.l3.randomizedIndirectIndexing) == "True"
                system.l3.TDR = options.l3_TDR #Set Tag-Data ratio for indirect
                system.l3.tags = IndirectTags()    #Select tag design as indirect
                system.l3.tags.assoc = options.l3_TDR*system.l3.tags.assoc                
                system.l3.tags.size = str(int(float(str(options.l3_TDR*system.l3.size)))) + "B"
                if(options.mirage_mode_l3 == "skew-vway-rand"):
                    system.l3.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l3 == "skew-vway-indirect"):
                    system.l3.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l3 == "skew-vway-rand-datareuserepl"):
                    system.l3.tags.data_repl_policy = "reuse"
                else:
                    fatal("Used a mirage_mode that is not supported")
            if (str(system.l3.vwayCache) == "True"):
                assert str(system.l3.randomizedIndexing) == "True"
                system.l3.TDR = options.l3_TDR #Set Tag-Data ratio for Vway
                system.l3.tags = VwayTags()    #Select tag design as Vway
                system.l3.tags.assoc = options.l3_TDR*system.l3.tags.assoc                
                system.l3.tags.size = str(int(float(str(options.l3_TDR*system.l3.size)))) + "B"
                if(options.mirage_mode_l3 == "skew-vway-rand"):
                    system.l3.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l3 == "skew-vway-indirect"):
                    system.l3.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l3 == "skew-vway-rand-datareuserepl"):
                    system.l3.tags.data_repl_policy = "reuse"
                else:
                    fatal("Used a mirage_mode that is not supported")
            if (str(system.l3.randomizedIndexing) == "True"):                
                system.l3.numSkews = options.l3_numSkews #Configure number of skews
                system.l3.mem_size = str(getMaxMemAddr(system.mem_ranges)+1) + "B"
                system.l3.tags.indexing_policy = SkewedAssocRand()
                if ( (int(system.l3.numSkews) > 1) and (str(system.l3.vwayCache) == "True") ) :
                    system.l3.replacement_policy = RandomSkewfairRP() 
                elif ( (int(system.l3.numSkews) > 1) ) :
                    system.l3.replacement_policy = RandomRP() #For more than 1 skew, use Random Repl
            if (str(system.l3.randomizedIndirectIndexing) == "True"):                
                system.l3.numSkews = options.l3_numSkews #Configure number of skews
                system.l3.mem_size = str(getMaxMemAddr(system.mem_ranges)+1) + "B"
                system.l3.tags.indexing_policy = SkewedAssocRandIndirect()
                if ( (int(system.l3.numSkews) > 1) and (str(system.l3.indirectCache) == "True") ) :
                    system.l3.replacement_policy = RandomSkewfairRP() 
                elif ( (int(system.l3.numSkews) > 1) ) :
                    system.l3.replacement_policy = RandomRP() #For more than 1 skew, use Random Repl
                
            #Set Cache Lookup Latency
            if ((str(system.l3.vwayCache) == "True") and (str(system.l3.randomizedIndexing) == "True")): # Lookup Latency is 24 for Vway + Rand (MIRAGE)
                system.l3.tag_latency      = l3latency + options.l3_EncrLat + 1 #4
                system.l3.tags.tag_latency = l3latency + options.l3_EncrLat + 1 #4
            elif ((str(system.l3.indirectCache) == "True") and (str(system.l3.randomizedIndirectIndexing) == "True")): # Lookup Latency is 24 for Vway + Rand (MIRAGE)
                print("Indirect and Indirect random indexing")
                system.l3.tag_latency      = l3latency + options.l3_EncrLat + 1 #4
                system.l3.tags.tag_latency = l3latency + options.l3_EncrLat + 1 #4
                ##TODO: sequentialAccess = True & Data_latency = 1. Then tag_latency will be 25.
            elif (str(system.l3.randomizedIndexing) == "True"): # Lookup Latency is 25 for Skewed Rand (Scatter-Cache)
                system.l3.tag_latency     = l3latency + options.l3_EncrLat #3
                system.l3.tags.tag_latency = l2latency + options.l3_EncrLat #3
            elif (str(system.l3.randomizedIndirectIndexing) == "True"): # Lookup Latency is 25 for Skewed Rand (Indirect index Cache)
                system.l3.tag_latency     = l3latency + options.l3_EncrLat #3
                system.l3.tags.tag_latency = l3latency + options.l3_EncrLat #3
            elif (str(system.l3.vwayCache) == "True" or str(system.l3.indirectCache) == "True"): # Lookup Latency is 21 for only Vway-Cache
                system.l3.tag_latency     = l3latency + 1
                system.l3.tags.tag_latency = l3latency + 1
    elif options.l2cache:
        # Provide a clock for the L2 and the L1-to-L2 bus here as they
        # are not connected using addTwoLevelCacheHierarchy. Use the
        # same clock as the CPUs.
        system.l2 = l2_cache_class(clk_domain=system.cpu_clk_domain,
                                   **_get_cache_opts('l2', options))

        system.tol2bus = L2XBar(clk_domain = system.cpu_clk_domain)
        
        system.l2.cpu_side = system.tol2bus.master
        system.l2.mem_side = system.tol3bus.slave
        l2latency = 10
        if options.mirage_mode_l2:
            if options.mirage_mode_l2 == "Baseline":
                system.l2.tag_latency     = l2latency
            elif options.mirage_mode_l2 == "BaselineRRIP":
                system.l2.tag_latency     = l2latency
                system.l2.replacement_policy = RRIPRP()
            elif options.mirage_mode_l2 == "BaselineBRRIP":
                system.l2.tag_latency     = l2latency
                system.l2.replacement_policy = BRRIPRP()
                system.l2.replacement_policy.btp = 5;
            elif options.mirage_mode_l2 == "scatter-cache":
                system.l2.skewedCache = True
                system.l2.randomizedIndexing = True
            elif options.mirage_mode_l2 == "vway-rand":
                system.l2.vwayCache = True
                system.l2.randomizedIndexing = True
            elif ((options.mirage_mode_l2 == "skew-vway-rand") or (options.mirage_mode_l2 == "skew-vway-rand-datareuserepl")):
                system.l2.vwayCache = True
                system.l2.randomizedIndexing = True
                system.l2.skewedCache = True
            elif options.mirage_mode_l2 == "cuckoo-skew-vway-rand":
                system.l2.vwayCache = True
                system.l2.randomizedIndexing = True
                system.l2.skewedCache = True
                system.l2.p2_on_conflict = True
                system.l2.cuckoo_on_conflict = True
            elif options.mirage_mode_l2 == "skew-vway-indirect":
                system.l2.indirectCache = True
                system.l2.randomizedIndirectIndexing = True
                system.l2.skewedCache = True
            else:
                fatal("Used a mirage_mode that is not supported")
            if (str(system.l2.vwayCache) == "True"):
                assert str(system.l2.randomizedIndexing) == "True" or str(system.l2.randomizedIndirectIndexing) == "True" 
                system.l2.TDR = options.l2_TDR #Set Tag-Data ratio for Vway
                system.l2.tags = VwayTags()    #Select tag design as Vway
                system.l2.tags.assoc = options.l2_TDR*system.l2.tags.assoc                
                system.l2.tags.size = str(int(float(str(options.l2_TDR*system.l2.size)))) + "B"
                if(options.mirage_mode_l2 == "skew-vway-rand"):
                    system.l2.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l2 == "skew-vway-indirect"):
                    system.l2.tags.data_repl_policy = "random"
                elif(options.mirage_mode_l2 == "skew-vway-rand-datareuserepl"):
                    system.l2.tags.data_repl_policy = "reuse"
                else:
                    fatal("Used a mirage_mode that is not supported")
            if (str(system.l2.randomizedIndexing) == "True"):                
                system.l2.numSkews = options.l2_numSkews #Configure number of skews
                system.l2.mem_size = str(getMaxMemAddr(system.mem_ranges)+1) + "B"
                system.l2.tags.indexing_policy = SkewedAssocRand()
                if ( (int(system.l2.numSkews) > 1) and (str(system.l2.vwayCache) == "True") ) :
                    system.l2.replacement_policy = RandomSkewfairRP() 
                elif ( (int(system.l2.numSkews) > 1) ) :
                    system.l2.replacement_policy = RandomRP() #For more than 1 skew, use Random Repl
            if (str(system.l2.randomizedIndirectIndexing) == "True"):                
                system.l2.numSkews = options.l2_numSkews #Configure number of skews
                system.l2.mem_size = str(getMaxMemAddr(system.mem_ranges)+1) + "B"
                system.l2.tags.indexing_policy = SkewedAssocRandIndirect()
                if ( (int(system.l2.numSkews) > 1) and (str(system.l2.vwayCache) == "True") ) :
                    system.l2.replacement_policy = RandomSkewfairRP() 
                elif ( (int(system.l2.numSkews) > 1) ) :
                    system.l2.replacement_policy = RandomRP() #For more than 1 skew, use Random Repl
                
            #Set Cache Lookup Latency
            if ((str(system.l2.vwayCache) == "True") and (str(system.l2.randomizedIndexing) == "True")): # Lookup Latency is 24 for Vway + Rand (MIRAGE)
                system.l2.tag_latency      = l2latency + options.l2_EncrLat + 1 #4
                system.l2.tags.tag_latency = l2latency + options.l2_EncrLat + 1 #4
                ##TODO: sequentialAccess = True & Data_latency = 1. Then tag_latency will be 25.
            elif (str(system.l2.randomizedIndexing) == "True"): # Lookup Latency is 25 for Skewed Rand (Scatter-Cache)
                system.l2.tag_latency     = l2latency + options.l2_EncrLat #3
                system.l2.tags.tag_latency = l2latency + options.l2_EncrLat #3
            elif (str(system.l2.randomizedIndirectIndexing) == "True"): # Lookup Latency is 25 for Skewed Rand (Indirect index Cache)
                system.l2.tag_latency     = l2latency + options.l2_EncrLat #3
                system.l2.tags.tag_latency = l2latency + options.l2_EncrLat #3
            elif (str(system.l2.vwayCache) == "True"): # Lookup Latency is 21 for only Vway-Cache
                system.l2.tag_latency     = l2latency + 1
                system.l2.tags.tag_latency = l2latency + 1
    if options.memchecker:
        system.memchecker = MemChecker()

    for i in range(options.num_cpus):
        if options.caches:
            icache = icache_class(**_get_cache_opts('l1i', options))
            dcache = dcache_class(**_get_cache_opts('l1d', options))

            # If we have a walker cache specified, instantiate two
            # instances here
            if walk_cache_class:
                iwalkcache = walk_cache_class()
                dwalkcache = walk_cache_class()
            else:
                iwalkcache = None
                dwalkcache = None

            if options.memchecker:
                dcache_mon = MemCheckerMonitor(warn_only=True)
                dcache_real = dcache

                # Do not pass the memchecker into the constructor of
                # MemCheckerMonitor, as it would create a copy; we require
                # exactly one MemChecker instance.
                dcache_mon.memchecker = system.memchecker

                # Connect monitor
                dcache_mon.mem_side = dcache.cpu_side

                # Let CPU connect to monitors
                dcache = dcache_mon

            # When connecting the caches, the clock is also inherited
            # from the CPU in question
            system.cpu[i].addPrivateSplitL1Caches(icache, dcache,
                                                  iwalkcache, dwalkcache)

            if options.memchecker:
                # The mem_side ports of the caches haven't been connected yet.
                # Make sure connectAllPorts connects the right objects.
                system.cpu[i].dcache = dcache_real
                system.cpu[i].dcache_mon = dcache_mon

        elif options.external_memory_system:
            # These port names are presented to whatever 'external' system
            # gem5 is connecting to.  Its configuration will likely depend
            # on these names.  For simplicity, we would advise configuring
            # it to use this naming scheme; if this isn't possible, change
            # the names below.
            if buildEnv['TARGET_ISA'] in ['x86', 'arm', 'riscv']:
                system.cpu[i].addPrivateSplitL1Caches(
                        ExternalCache("cpu%d.icache" % i),
                        ExternalCache("cpu%d.dcache" % i),
                        ExternalCache("cpu%d.itb_walker_cache" % i),
                        ExternalCache("cpu%d.dtb_walker_cache" % i))
            else:
                system.cpu[i].addPrivateSplitL1Caches(
                        ExternalCache("cpu%d.icache" % i),
                        ExternalCache("cpu%d.dcache" % i))

        system.cpu[i].createInterruptController()

        if options.l2cache and options.l3cache:
            print(i)
            
            system.cpu[i].l2 =  l2_cache_class(clk_domain=system.cpu_clk_domain,
                                **_get_cache_opts('l2', options))
            system.cpu[i].tol2bus =  L2XBar(clk_domain = system.cpu_clk_domain)
            system.cpu[i].l2.cpu_side = system.cpu[i].tol2bus.master
            system.cpu[i].l2.mem_side = system.tol3bus.slave
            
            
                #system.cpu[i].tol2bus = system.cpu[i-1].tol2bus
                
            system.cpu[i].connectAllPorts(system.cpu[i].tol2bus, system.membus)
            
           #system.cpu[i].connectAllPorts(system.cpu[i].tol2bus, system.membus)
            
        # if options.l3cache:
        #     system.cpu[i].connectAllPorts(system.tol3bus,system.membus)
        elif options.l2cache:
            system.cpu[i].connectAllPorts(system.tol2bus,system.membus)
        elif options.external_memory_system:
            system.cpu[i].connectUncachedPorts(system.membus)
        else:
            system.cpu[i].connectAllPorts(system.membus)

    return system

# ExternalSlave provides a "port", but when that port connects to a cache,
# the connecting CPU SimObject wants to refer to its "cpu_side".
# The 'ExternalCache' class provides this adaptation by rewriting the name,
# eliminating distracting changes elsewhere in the config code.
class ExternalCache(ExternalSlave):
    def __getattr__(cls, attr):
        if (attr == "cpu_side"):
            attr = "port"
        return super(ExternalSlave, cls).__getattr__(attr)

    def __setattr__(cls, attr, value):
        if (attr == "cpu_side"):
            attr = "port"
        return super(ExternalSlave, cls).__setattr__(attr, value)

def ExternalCacheFactory(port_type):
    def make(name):
        return ExternalCache(port_data=name, port_type=port_type,
                             addr_ranges=[AllMemory])
    return make

# Get the maximum memory address possible from the
# address ranges specified in the system.mem_ranges
def getMaxMemAddr(addr_ranges):
    max_addr = 0
    for r in addr_ranges:
        if max_addr < int(r.end):
            max_addr = int(r.end)
    return max_addr
