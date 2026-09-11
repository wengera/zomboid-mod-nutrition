-- The empty-version-dir arm: this mod's 42.20/ folder holds a mod.info and NOTHING else -- no
-- media/ at all -- so this file under common/ is the mod's entire payload. If this global is
-- present, a version folder with no media/ does not suppress the common/ tree.
TKX_CommonOnly = { version = 1 }
