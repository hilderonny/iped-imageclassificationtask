# Transcription and translation of audio files
# Configuration
# =============
# enabling: enableImageClassification
# Config file: ImageClassificationTask.txt

import time
import logging
import json
import requests

API_URL = None

def readJsonFile(file_path):
    with open(file_path, "r", encoding="utf-8") as json_file:
        file_contents = json_file.read()
    parsed_json = json.loads(file_contents)
    return parsed_json

class ImageClassificationTask:

    enabled = False

    def isEnabled(self):
        return ImageClassificationTask.enabled

    def getConfigurables(self):
        from iped.engine.config import DefaultTaskPropertiesConfig
        return [DefaultTaskPropertiesConfig("enableImageClassification", "ImageClassification.txt")]

    def init(self, configuration):
        taskConfig = configuration.getTaskConfigurable("ImageClassification.txt")
        ImageClassificationTask.enabled = taskConfig.isEnabled()
        if not ImageClassificationTask.enabled:
            return
        extraProps = taskConfig.getConfiguration()
        global API_URL
        taskBridgeUrl = extraProps.getProperty("taskBridgeUrl")
        if not taskBridgeUrl.endswith("/"):
            taskBridgeUrl = f"{taskBridgeUrl}/"
        API_URL = f"{taskBridgeUrl}api/"

    def finish(self):
        return
        
    def process(self, item):
        item_name = item.getName()
        # Process only if not already in cache, therefor hashing must be enabled
        hash = item.getHash()
        if (hash is None) or (len(hash) < 1):
            return
        media_type = item.getMediaType().toString()

        if not (media_type.startswith('image')):
            return

        result = self.process_via_api(item, hash)

        if "predictions" in result:
            item.setExtraAttribute("image:classification:classes", result["predictions"])
        if "name" in result:
            item.setExtraAttribute("image:classification:bestclass", result["name"])
        if "probability" in result:
            item.setExtraAttribute("image:classification:probability", result["probability"])
        logging.info("Processed item %s: %s", item_name, result)

    def process_via_api(self, item, hash):
        result = {}
        
        classifyimage_fp = open(item.getTempFile().getAbsolutePath(), "rb")
        classifyimage_files = { "file" : classifyimage_fp }
        classifyimage_json = { "type" : "classifyimage", "data" : { "targetlanguage" : "de", "numberofpredictions" : "10" } }

        # Add classifyimage task and upload file
        add_classifyimage_response = requests.post(f"{API_URL}tasks/add/", files=classifyimage_files, data={ "json" : json.dumps(classifyimage_json) })
        if add_classifyimage_response.status_code != 200:
            result["error"] = "Error adding classifyimage task"
            return result
        task_classifyimage_id = add_classifyimage_response.json()["id"]

        # Wait for classifyimage task completion
        task_classifyimage_completed = False
        while not task_classifyimage_completed:
            status_classifyimage_response = requests.get(f"{API_URL}tasks/status/{task_classifyimage_id}")
            if status_classifyimage_response.status_code != 200:
                result["error"] = "Error requesting classifyimage task status"
                return result
            status_classifyimage = status_classifyimage_response.json()["status"]
            if status_classifyimage == "completed":
                task_classifyimage_completed = True
            else:
                time.sleep(3)

        # Request classifyimage result
        result_classifyimage_response = requests.get(f"{API_URL}tasks/result/{task_classifyimage_id}")
        if result_classifyimage_response.status_code != 200:
            result["error"] = "Error requesting classifyimage task result"
            return result
        classifyimage_result = result_classifyimage_response.json()

        # Delete classifyimage task
        delete_classifyimage_response = requests.delete(f"{API_URL}tasks/remove/{task_classifyimage_id}")
        if delete_classifyimage_response.status_code != 200:
            result["error"] = "Error deleting classifyimage task"
            return result

        if "error" in classifyimage_result["result"]:
            result["error"] = classifyimage_result["result"]["error"]
        else:
            # Collect results
            predictions = classifyimage_result["result"]["predictions"]
            result["predictions"] = predictions
            result["name"] = predictions[0]["name"]
            result["probability"] = predictions[0]["probability"]

        return result