# Copyright (c) 2022 The Regents of the University of California
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

"""
This script further shows an example of booting an ARM based full system Ubuntu
disk image. This simulation boots the disk image using 2 TIMING CPU cores. The
simulation ends when the startup is completed successfully (i.e. when an
`m5_exit instruction is reached on successful boot).

Usage
-----

```
scons build/ARM/gem5.opt -j<NUM_CPUS>
./build/ARM/gem5.opt configs/example/gem5_library/arm-ubuntu-run.py
```

"""

from m5.objects import (
    ArmDefaultRelease,
    VExpress_GEM5_Foundation,
)

from gem5.coherence_protocol import CoherenceProtocol
from gem5.components.boards.arm_board import ArmBoard
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource, CheckpointResource
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires

#2024/07/16 won.hur : Need to import m5 for checkpoints (m5.checkpoint())
import m5

#2024/07/16 won.hur : simulator::checkpoint needs to know the os.path
import os

# This runs a check to ensure the gem5 binary is compiled for ARM and the
# protocol is CHI.

requires(isa_required=ISA.ARM)

from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)


# 2024/07/16 won.hur : Add datatime for timestamp printouts 
from datetime import datetime
now = datetime.now()
print("ESCAL : Simulation time stamp(START) : ", now.strftime("%Y-%m-%d %H:%M:%S"))

# 2024/07/16 won.hur : To use ExitEvent(for checkpointing...), I need to import exit_event from gem5 STD LIB
from gem5.simulate.exit_event import ExitEvent


# Here we setup the parameters of the l1 and l2 caches.
cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="16kB", l1i_size="16kB", l2_size="256kB"
)

# Memory: Dual Channel DDR4 2400 DRAM device.

memory = DualChannelDDR4_2400(size="2GB")

# Here we setup the processor. We use a simple TIMING processor. The config
# script was also tested with ATOMIC processor.
# 2024/07/16 won.hur : changed num_cores from 2 to 1 (to have a clear view on memory effects using SMMU) 
#processor = SimpleProcessor(cpu_type=CPUTypes.TIMING, num_cores=2, isa=ISA.ARM)
processor = SimpleProcessor(cpu_type=CPUTypes.TIMING, num_cores=1, isa=ISA.ARM)

# The ArmBoard requires a `release` to be specified. This adds all the
# extensions or features to the system. We are setting this to Armv8
# (ArmDefaultRelease) in this example config script.
release = ArmDefaultRelease()

# The platform sets up the memory ranges of all the on-chip and off-chip
# devices present on the ARM system.

platform = VExpress_GEM5_Foundation()


#2024/07/16 won.hur : For test..
command = "m5 exit;" \
        + "echo 'ESCAL : This is called from the restore script'';" \
        + "sleep 1;" \
        + "m5 exit;"

# Here we setup the board. The ArmBoard allows for Full-System ARM simulations.

board = ArmBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
    release=release,
    platform=platform,
)

# Here we set a full system workload. The "arm64-ubuntu-20.04-boot" boots
# Ubuntu 20.04.
board.set_workload(
    obtain_resource("arm64-ubuntu-20.04-boot", resource_version="2.0.0")
)

# 2024/07/16 won.hur : Adding kernel argument to not execute default script
board.append_kernel_arg("interactive=true")

#board.set_kernel_disk_workload(
#    kernel=obtain_resource(
#        "arm64-linux-kernel-5.4.49", resource_version="1.0.0"
#    ),
#    disk_image=obtain_resource(
#        "arm-ubuntu-22.04-img", resource_version="1.0.0"
#    ),
#    bootloader=obtain_resource("arm64-bootloader-foundation", resource_version="1.0.0"),
#    checkpoint=CheckpointResource("checkpoint_arm_ubuntu2204_20240717a"),
#    readfile_contents=command,
#)


# 2024/07/16 won.hur : Newly defined on_exit() function for checkpointing
#                      Make sure to rename the checkpoints for each testings
def on_exit():
    print("ESCAL : on_exit() #1 called! Reset Stats!")
    m5.stats.reset()
    yield False #2024/07/16 won.hur : False would not exit the simulation, where TRUE will terminate the simulation.
    print("ESCAL : on_exit() #2 called!")
    yield True

# 2024/07/16 won.hur : Newly defined on_work_begin() function to reset stats (not connected yet)
def on_work_begin():
    print("ESCAL : on_work_begin() Reset Stats!")
    m5.stats.reset()
    yield False

# 2024/07/16 won.hur : Newly defined on_work_end() function to notify that the workload is done
def on_work_end():
    print("ESCAL : on_work_end()")
    yield True


# We define the system with the aforementioned system defined.

simulator = Simulator(
        board=board,
        on_exit_event={
            ExitEvent.EXIT: on_exit(),
            ExitEvent.WORKBEGIN: on_work_begin(),
            ExitEvent.WORKEND: on_work_end(),
            },
        checkpoint_path=os.path.join(
            os.getcwd(),
            "checkpoint_arm_ubuntu2004_20240717b"
            )
        )

# Once the system successfully boots, it encounters an
# `m5_exit instruction encountered`. We stop the simulation then. When the
# simulation has ended you may inspect `m5out/board.terminal` to see
# the stdout.

simulator.run()



# 2024/07/16 won.hur : Add timestamp to notify simulation end time 
now = datetime.now()
print("ESCAL : Simulation time stamp(END) : ", now.strftime("%Y-%m-%d %H:%M:%S"))
