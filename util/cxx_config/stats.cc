/*
 * Copyright (c) 2014 ARM Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @file
 *
 *  C++-only configuration stats handling example
 *
 *  Register with: gem5::statistics::registerHandlers(statsReset, statsDump)
 */

#include <iostream>
#include <list>

#include "base/statistics.hh"
#include "stats.hh"

namespace CxxConfig
{

void statsPrepare()
{
    std::list<gem5::statistics::Info *> stats = gem5::statistics::statsList();

    /* gather_stats -> prepare */
    for (auto i = stats.begin(); i != stats.end(); ++i)
        (*i)->prepare();
}

void statsDump()
{
    std::cerr << "Stats dump\n";

    gem5::statistics::processDumpQueue();

    std::list<gem5::statistics::Info *> stats = gem5::statistics::statsList();

    statsPrepare();

    /* gather_stats -> convert_value */
    for (auto i = stats.begin(); i != stats.end(); ++i) {
        gem5::statistics::Info *stat = *i;

        gem5::statistics::ScalarInfo *scalar =
            dynamic_cast<gem5::statistics::ScalarInfo *>(stat);
        gem5::statistics::VectorInfo *vector =
            dynamic_cast<gem5::statistics::VectorInfo *>(stat);

        if (scalar) {
            std::cerr << "SCALAR " << stat->name << ' '
                << scalar->value() << '\n';
        } else if (vector) {
            gem5::statistics::VResult results = vector->value();

            unsigned int index = 0;
            for (auto e = results.begin(); e != results.end(); ++e) {
                std::cerr << "VECTOR " << stat->name << '[' << index
                    << "] " << (*e) << '\n';
                index++;
            }
            std::cerr << "VTOTAL " << stat->name << ' '
                << vector->total() << '\n';
        } else {
            std::cerr << "?????? " << stat->name << '\n';
        }
    }
}

void statsReset()
{
    std::cerr << "Stats reset\n";

    gem5::statistics::processResetQueue();
}

void statsEnable()
{
    std::list<gem5::statistics::Info *> stats = gem5::statistics::statsList();

    for (auto i = stats.begin(); i != stats.end(); ++i)
        (*i)->enable();
}

}
