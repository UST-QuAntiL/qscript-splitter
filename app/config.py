# ******************************************************************************
#  Copyright (c) 2021 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************

import os

basedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    RESULT_FOLDER = os.environ.get('RESULT_FOLDER') or os.path.join(basedir, 'generated-files')
    KNOWLEDGE_BASE_FOLDER = os.environ.get('KNOWLEDGE_BASE_FOLDER') or os.path.join(basedir, 'knowledge_base')

    # number of consecutive lines of classical code allowed in quantum parts
    SPLITTING_THRESHOLD = 2

    # Clear upload and result folders first (for debugging purposes)
    CLEAR_FILES_ON_NEW_REQUEST = os.environ.get('CLEAR_FILES_ON_NEW_REQUEST') or False
