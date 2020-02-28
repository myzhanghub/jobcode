#/bin/bash
sort -n 1.txt |awk -F ':' '{print $1}'|uniq >key.txt
for key in `cat key.txt`
do
  echo "[$key]"
  awk -F ':' '$1=="'$key'" { print $2}' 1.txt
done