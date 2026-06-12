/**
 * City identity config — single source of truth.
 *
 * Imports the git-tracked symlink `frontend/city.config.json -> ../city.config.json`.
 * This is the ONLY module that touches the symlinked JSON, so if the bundler ever
 * rejects the symlink the blast radius is one file (replace symlink with a synced copy).
 */
import cityConfig from "../../city.config.json";

export default cityConfig;
