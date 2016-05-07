#!/bin/bash

export SERVER_A="A.ini"

export CLIENT_A="a.ini"
export CLIENT_B="b.ini"
export CLIENT_C="c.ini"

setup-fixture() {
    start_server "$SERVER_A"
    wait_for_server "$SERVER_A"
    select_server "$SERVER_A"
    select_client "$CLIENT_A"
}
