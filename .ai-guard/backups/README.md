ACL backup files are stored here by lock.ps1.
Each subdirectory is named with a timestamp: YYYY-MM-DD_HH-mm-ss/
Each .acl file is a binary dump produced by: icacls <path> /save <file> /T
These files are NOT committed to git.
