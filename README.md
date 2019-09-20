veos booted w/ the vmdk and did `zerotouch disable` to ensure that it allows for saving configs when the container boots up (so it doesnt break napalm)


eos show ip ospf nei template:
Value NEIGHBOR_ID (\d+.\d+.\d+.\d+)
Value VRF (\S+)
Value PRIORITY (\d+)
Value STATE (\S+)
Value DEAD_TIME (\d+:\d+:\d+)
Value ADDRESS (\d+.\d+.\d+.\d+)
Value INTERFACE (\S+)

Start
  ^${NEIGHBOR_ID}\s+\d+\s+${VRF}\s+${PRIORITY}\s+${STATE}\s+${DEAD_TIME}\s+${ADDRESS}\s+${INTERFACE} -> Record
  
  
 