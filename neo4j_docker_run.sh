#!/usr/bin/env bash
docker run --publish=7474:7474 --publish=7687:7687 --volume=zolse:/data --volume=zolse:/logs --env=NEO4J_dbms_active__database=zolse18.db -d neo4j:3.5.3