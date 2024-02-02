# Transcription and translation of audio files
# Configuration
# =============
# enabling: enableImageClassification
# Config file: ImageClassificationTask.txt

import os
import time
import logging
import json
import shutil
import stat
import requests

logging.basicConfig(format='%(asctime)s [%(levelname)s] [ImageClassificationTask.py] %(message)s', level=logging.DEBUG)

# Configuration properties
enableProp = "enableImageClassification"
configFile = "ImageClassification.txt"
inputDirectoryProp = "inputDirectory"
outputDirectoryProp = "outputDirectory"
useForensicTaskBridgeProp = "useForensicTaskBridge"
forensicTaskBridgeApiUrlProp = "forensicTaskBridgeApiUrl"
forensicTaskBridgeShareDirectoryProp = "forensicTaskBridgeShareDirectory"

INPUT_DIR = None
OUTPUT_DIR = None
USE_API = False
API_URL = None
API_SHARE_DIR = None

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
        return [DefaultTaskPropertiesConfig(enableProp, configFile)]

    def init(self, configuration):
        taskConfig = configuration.getTaskConfigurable(configFile)
        ImageClassificationTask.enabled = taskConfig.isEnabled()
        if not ImageClassificationTask.enabled:
            return
        extraProps = taskConfig.getConfiguration()
        global INPUT_DIR, OUTPUT_DIR, USE_API, API_URL, API_SHARE_DIR
        INPUT_DIR = extraProps.getProperty(inputDirectoryProp)
        OUTPUT_DIR = extraProps.getProperty(outputDirectoryProp)
        USE_API = True if extraProps.getProperty(useForensicTaskBridgeProp) == "true" else False
        API_URL = extraProps.getProperty(forensicTaskBridgeApiUrlProp)
        API_SHARE_DIR = extraProps.getProperty(forensicTaskBridgeShareDirectoryProp)

    def finish(self):
        return
        
    # Process an Item object. This method is executed on all case items.
    # It can access any method of Item class and store results as a new extra attribute.
    #
    #  Some Getters:
    #  String:  getName(), getExt(), getType(), getPath(), getHash(), getMediaType().toString(), getCategories() (categories separated by | )
    #  Date:    getModDate(), getCreationDate(), getAccessDate() (podem ser nulos)
    #  Boolean: isDeleted(), isDir(), isRoot(), isCarved(), isSubItem(), isTimedOut(), hasChildren()
    #  Long:    getLength()
    #  Metadata getMetadata()
    #  Object:  getExtraAttribute(String key) (returns an extra attribute)
    #  String:  getParsedTextCache() (returns item extracted text, if this task is placed after ParsingTask)
    #  File:    getTempFile() (returns a temp file with item content)
    #  BufferedInputStream: getBufferedInputStream() (returns an InputStream with item content)
    #
    #  Some Setters: 
    #           setToIgnore(boolean) (ignores the item and excludes it from processing and case)
    #           setAddToCase(boolean) (inserts or not item in case, after being processed: default true)
    #           addCategory(String), removeCategory(String), setMediaTypeStr(String)
    #              setExtraAttribute(key, value), setParsedTextCache(String)
    #
    def process(self, item):
        item_name = item.getName()
        # Process only if not already in cache, therefor hashing must be enabled
        hash = item.getHash()
        if (hash is None) or (len(hash) < 1):
            return
        media_type = item.getMediaType().toString()

        if not (media_type.startswith('image')):
            return

        if USE_API == True:
            result = self.process_via_api(item, hash)
        else:
            result = self.process_locally(item, hash)

        if "predictions" in result:
            item.setExtraAttribute("image:classification:classes", result["predictions"])
            #meta_data.set("image:classification:classes", str(result["predictions"]))
        if "name" in result:
            item.setExtraAttribute("image:classification:bestclass", result["name"])
            #meta_data.set("image:classification:bestclass", str(result["name"]))
        if "probability" in result:
            item.setExtraAttribute("image:classification:probability", result["probability"])
            #meta_data.set("image:classification:probability", str(result["probability"]))
        logging.info("Processed item %s: %s", item_name, result)

    # Result format
    #   predictions []
    #   name
    #   probability

    def process_locally(self, item, hash):
        source_file_path = item.getTempFile().getAbsolutePath()

        # Determine file name with hash
        input_file_path = os.path.join(INPUT_DIR, hash)
        output_file_path = os.path.join(OUTPUT_DIR, hash + ".json")

        # Check whether result file already exists in output directory
        if os.path.isfile(output_file_path) == False:
            # If not, copy source file into input directory
            shutil.copy(source_file_path, input_file_path)
            os.chmod(input_file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO ) # Let the background process delete the file afterwards
            # Wait until the result file was created in output directory
            while os.path.isfile(output_file_path) == False:
                time.sleep(5)
        # Process result file and extract metadata
        result = readJsonFile(output_file_path)
        return result

    def process_via_api(self, item, hash):
        result = {}
        # Copy file to share folder
        source_file_path = item.getTempFile().getAbsolutePath()
        share_file_path = os.path.join(API_SHARE_DIR, hash)
        shutil.copy(source_file_path, share_file_path)
        # Add classification task
        response = requests.post(f"{API_URL}tasks/classifyimage/add/{hash}/de")
        if response.status_code != 200:
            logging.error(f"Cannot access {API_URL}tasks/classifyimage/add/{hash}/de")
            return result
        add_classification_json_result = response.json()
        print(add_classification_json_result)
        classification_task_id = add_classification_json_result["id"]
        # Wait for completion
        while requests.get(f"{API_URL}tasks/status/{classification_task_id}").json()["status"] != "done":
            time.sleep(5)
        classification_result = requests.get(f"{API_URL}tasks/result/{classification_task_id}").json()
        print(classification_result)
        if "error" in classification_result["result"]:
            result["error"] = classification_result["result"]["error"]
        else:
            # Collect results
            result["predictions"] = classification_result["result"]["predictions"]
            result["name"] = classification_result["result"]["name"]
            result["probability"] = classification_result["result"]["probability"]
        # Delete task from bridge
        delete_result = requests.delete(f"{API_URL}tasks/remove/{classification_task_id}")
        print(delete_result)
        print(result)
        return result
