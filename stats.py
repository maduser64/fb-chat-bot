import io
import json
import time
import threading

class Stats:
    """Manages stats file"""

    def __init__(self, stats_file):
        self.__dirty = False
        self.stats_file = stats_file
        self.last_update = time.time()

        with open(stats_file, "r") as infile:
            #text = infile.read()
            self.vals = json.load(infile)
        
        self.vals["times_launched"] += 1
        
        self.updateStats()


    def updateStats(self):
        """Every 10s writes to stats file new updates, if there are any"""
        threading.Timer(10, self.updateStats).start()
        
        # Keeps track of uptime
        dif = time.time() - self.last_update
        if dif >= 60:
            self.vals["uptime_minutes"] += 1
            self.__dirty = True
            self.last_update = time.time()

        # Writes only if data is modified
        if self.__dirty:
            with open(self.stats_file, "w") as outfile:
                json.dump(self.vals, outfile, indent = "\t")
            self.__dirty = False

    def updateCommandsExecuted(self, name_code, command):
        self.vals["commands_executed"] += 1

        cmd = self.vals["commands"].get(command)
        if cmd:
            cmd["count"] += 1
            cmd["last_time"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
            
            for item in cmd["by_user"]:
                val = item.get(name_code)
                if val:
                    item[name_code] += 1
                    break
            # First time executed by user
            else: cmd["by_user"].append({ name_code : 1 })

        # First time executed
        else:
            self.vals["commands"][command] = { "count" : 1 }
            self.vals["commands"][command]["last_time"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
            self.vals["commands"][command]["by_user"] = [{ name_code : 1 }]
            
        self.makeDirty()

    def updateCommandsError(self):
        self.vals["commands_error"] += 1
        self.makeDirty()


    def updateMessagesSent(self):
        self.vals["messages_sent"] += 1
        self.makeDirty()
      
    def makeDirty(self):
        self.__dirty = True

