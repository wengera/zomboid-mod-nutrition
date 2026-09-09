"""pzt — orchestrator for the PZ integration-test pipeline.

Phases (docs/testing/pipeline-design.md):
  provision  boot a fresh server, let driven clients create the world + their
             characters, snapshot everything as a golden fixture (once per
             game/mod-set version)
  boot       restore a fixture's server world into a run dir and start it (~15 s)
  attach     restore a fixture's client cache, launch the client, wait until it
             is in-world (~30 s; no character-creation screens)
  run        boot + attach + (test slot) + graceful teardown + report
"""
