try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import json
import hashlib
import re
import os
import logging
import pkg_resources
import xml.etree.ElementTree as ET
import mimetypes

from functools import partial

import zipfile
from django.core.files import File
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone
from webob import Response
from storages.backends.s3boto import S3BotoStorage

from xblock.core import XBlock
from xblock.fields import Scope, String, Float, Boolean, Dict, DateTime, Integer
from xblockutils.resources import ResourceLoader
from web_fragments.fragment import Fragment

# Make '_' a no-op so we can scrape strings
_ = lambda text: text
loader = ResourceLoader(__name__)
log = logging.getLogger(__name__)


class FileIter(object):
    def __init__(self, _file, _type='application/octet-stream'):
        self._file = _file
        self.wrapper = lambda d: d

    def __iter__(self):
        try:
            while True:
                data = self._file.read(65536)
                if not data:
                    return
                yield self.wrapper(data)
        finally:
            self._file.close()


@XBlock.needs('i18n')
class ScormXBlock(XBlock):

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Scorm",
        scope=Scope.settings,
    )
    scorm_file = String(
        display_name=_("Upload scorm file"),
        scope=Scope.settings,
    )
    path_index_page = String(
        display_name=_("Path to the index page in scorm file"),
        scope=Scope.settings,
    )
    scorm_file_meta = Dict(
        scope=Scope.content
    )
    version_scorm = String(
        default="SCORM_12",
        scope=Scope.settings,
    )
    # save completion_status for SCORM_2004
    lesson_status = String(
        scope=Scope.user_state,
        default='not attempted'
    )
    success_status = String(
        scope=Scope.user_state,
        default='unknown'
    )
    data_scorm = Dict(
        scope=Scope.user_state,
        default={}
    )
    lesson_score = Float(
        scope=Scope.user_state,
        default=0
    )
    weight = Float(
        default=1,
        scope=Scope.settings
    )
    has_score = Boolean(
        display_name=_("Scored"),
        help=_("Select False if this component will not receive a numerical score from the Scorm"),
        default=True,
        scope=Scope.settings
    )
    icon_class = String(
        default="video",
        scope=Scope.settings,
    )
    width = Integer(
        display_name=_("Display Width (px)"),
        help=_('Width of iframe, if empty, the default 100'),
        scope=Scope.settings
    )
    height = Integer(
        display_name=_("Display Height (px)"),
        help=_('Height of iframe'),
        default=450,
        scope=Scope.settings
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        context_html = self.get_context_student()
        template = loader.render_django_template(
            'static/html/scormxblock.html',
            context=context_html,
            i18n_service=self.runtime.service(self, 'i18n')
        )
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/scormxblock.js"))
        settings = {
            'version_scorm': self.version_scorm
        }
        frag.initialize_js('ScormXBlock', json_args=settings)
        return frag

    def studio_view(self, context=None):
        context_html = self.get_context_studio()
        template = loader.render_django_template(
            'static/html/studio.html',
            context=context_html,
            i18n_service=self.runtime.service(self, 'i18n')
        )
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/studio.js"))
        frag.initialize_js('ScormStudioXBlock')
        return frag

    @XBlock.handler
    def studio_submit(self, request, suffix=''):
        self.display_name = request.params['display_name']
        self.width = request.params['width']
        self.height = request.params['height']
        self.has_score = request.params['has_score']
        self.icon_class = 'problem' if self.has_score == 'True' else 'video'

        if hasattr(request.params['file'], 'file'):
            scorm_file = request.params['file'].file

            if default_storage.exists(self.folder_base_path):
                log.info(
                    'Removing previously uploaded "%s"', self.folder_base_path
                )
                self.recursive_delete(self.folder_base_path)

            self.scorm_file_meta['sha1'] = self.get_sha1(scorm_file)
            self.scorm_file_meta['name'] = scorm_file.name
            self.scorm_file_meta['path'] = path = self._file_storage_path()
            self.scorm_file_meta['last_updated'] = timezone.now().strftime(DateTime.DATETIME_FORMAT)

            # First, extract zip file
            with zipfile.ZipFile(scorm_file, "r") as scorm_zipfile:
                for zipinfo in scorm_zipfile.infolist():
                    if not zipinfo.filename.endswith("/"):
                        zip_file = BytesIO()
                        zip_file.write(scorm_zipfile.open(zipinfo.filename).read())
                        default_storage.save(
                            os.path.join(self.folder_path, zipinfo.filename),
                            zip_file,
                        )
                        zip_file.close()

            scorm_file.seek(0)

            # Then, save scorm file in the storage for mobile clients
            default_storage.save(path, File(scorm_file))
            self.scorm_file_meta['size'] = default_storage.size(path)
            log.info('"{}" file stored at "{}"'.format(scorm_file, path))

            self.set_fields_xblock()

        return Response(json.dumps({'result': 'success'}), content_type='application/json', charset="utf8")

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        name = data.get('name')
        if name in ['cmi.core.lesson_status', 'cmi.completion_status']:
            return {'value': self.lesson_status}
        elif name == 'cmi.success_status':
            return {'value': self.success_status}
        elif name in ['cmi.core.score.raw', 'cmi.score.raw']:
            return {'value': self.lesson_score * 100}
        else:
            return {'value': self.data_scorm.get(name, '')}

    @XBlock.json_handler
    def scorm_set_value(self, data, suffix=''):
        context = {'result': 'success'}
        name = data.get('name')

        if name in ['cmi.core.lesson_status', 'cmi.completion_status']:
            self.lesson_status = data.get('value')
            if self.has_score and data.get('value') in ['completed', 'failed', 'passed']:
                self.publish_grade()
                context.update({"lesson_score": self.format_lesson_score})

        elif name == 'cmi.success_status':
            self.success_status = data.get('value')
            if self.has_score:
                if self.success_status == 'unknown':
                    self.lesson_score = 0
                self.publish_grade()
                context.update({"lesson_score": self.format_lesson_score})
        elif name in ['cmi.core.score.raw', 'cmi.score.raw'] and self.has_score:
            self.lesson_score = float(data.get('value', 0))/100.0
            self.publish_grade()
            context.update({"lesson_score": self.format_lesson_score})
        else:
            self.data_scorm[name] = data.get('value', '')

        context.update({"completion_status": self.get_completion_status()})
        return context

    def publish_grade(self):
        if self.lesson_status == 'failed' or (self.version_scorm == 'SCORM_2004'
                                              and self.success_status in ['failed', 'unknown']):
            self.runtime.publish(
                self,
                'grade',
                {
                    'value': 0,
                    'max_value': self.weight,
                })
        else:
            self.runtime.publish(
                self,
                'grade',
                {
                    'value': self.lesson_score,
                    'max_value': self.weight,
                })

    def max_score(self):
        """
        Return the maximum score possible.
        """
        return self.weight if self.has_score else None

    def get_context_studio(self):
        return {
            'field_display_name': self.fields['display_name'],
            'field_scorm_file': self.fields['scorm_file'],
            'field_has_score': self.fields['has_score'],
            'field_width': self.fields['width'],
            'field_height': self.fields['height'],
            'scorm_xblock': self
        }

    def get_context_student(self):
        scorm_file_path = ''
        if self.scorm_file:
            if isinstance(default_storage, S3BotoStorage):
                scorm_file_path = self.runtime.handler_url(self, 's3_file', self.scorm_file)
            else:
                scorm_file_path = default_storage.url(self.scorm_file)

        return {
            'scorm_file_path': scorm_file_path,
            'completion_status': self.get_completion_status(),
            'scorm_xblock': self
        }

    @XBlock.handler
    def s3_file(self, request, suffix=''):
        filename = suffix.split('?')[0]
        _type, encoding = mimetypes.guess_type(filename)
        _type = _type or 'application/octet-stream'
        res = Response(content_type=_type)
        res.app_iter = FileIter(default_storage.open(filename, 'rb'), _type)
        return res

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def set_fields_xblock(self):
        self.path_index_page = 'index.html'

        imsmanifest_path = os.path.join(self.folder_path, "imsmanifest.xml")
        try:
            imsmanifest_file = default_storage.open(imsmanifest_path)
        except IOError:
            pass
        else:
            tree = ET.parse(imsmanifest_file)
            imsmanifest_file.seek(0)
            namespace = ''
            for node in [node for _, node in ET.iterparse(imsmanifest_file, events=['start-ns'])]:
                if node[0] == '':
                    namespace = node[1]
                    break
            root = tree.getroot()

            if namespace:
                resource = root.find('{{{0}}}resources/{{{0}}}resource'.format(namespace))
                schemaversion = root.find('{{{0}}}metadata/{{{0}}}schemaversion'.format(namespace))
            else:
                resource = root.find('resources/resource')
                schemaversion = root.find('metadata/schemaversion')

            if resource:
                self.path_index_page = resource.get('href')
            if (schemaversion is not None) and (re.match('^1.2$', schemaversion.text) is None):
                self.version_scorm = 'SCORM_2004'
            else:
                self.version_scorm = 'SCORM_12'

        self.scorm_file = os.path.join(self.folder_path, self.path_index_page)

    def get_completion_status(self):
        _ = self.runtime.service(self, 'i18n').ugettext
        completion_status = self.lesson_status
        if self.version_scorm == 'SCORM_2004' and self.success_status != 'unknown':
            completion_status = self.success_status
        return _(completion_status)

    def _file_storage_path(self):
        """
        Get file path of storage.
        """
        path = (
            '{folder_path}{ext}'.format(
                folder_path=self.folder_path,
                ext=os.path.splitext(self.scorm_file_meta['name'])[1]
            )
        )
        return path

    @property
    def folder_base_path(self):
        """
        Path to the folder where packages will be extracted.
        """
        return os.path.join(self.location.block_type, self.location.course, self.location.block_id)

    @property
    def folder_path(self):
        """
        This path needs to depend on the content of the scorm package. Otherwise,
        served media files might become stale when the package is update.
        """
        return os.path.join(self.folder_base_path, self.scorm_file_meta["sha1"])

    def get_sha1(self, file_descriptor):
        """
        Get file hex digest (fingerprint).
        """
        block_size = 8 * 1024
        sha1 = hashlib.sha1()
        for block in iter(partial(file_descriptor.read, block_size), b''):
            sha1.update(block)
        file_descriptor.seek(0)
        return sha1.hexdigest()

    @property
    def format_lesson_score(self):
        return '{:.2f}'.format(self.lesson_score)

    def student_view_data(self):
        """
        Inform REST api clients about original file location and it's "freshness".
        Make sure to include `student_view_data=scormxblock` to URL params in the request.
        """
        if self.scorm_file and self.scorm_file_meta:
            return {
                'last_modified': self.scorm_file_meta.get('last_updated', ''),
                'scorm_data': default_storage.url(self._file_storage_path()),
                'size': self.scorm_file_meta.get('size', 0),
                'index_page': self.path_index_page,
            }
        return {}

    def recursive_delete(self, root):
        """
        Recursively delete the contents of a directory in the Django default storage.
        Unfortunately, this will not delete empty folders, as the default FileSystemStorage
        implementation does not allow it.
        """
        directories, files = default_storage.listdir(root)
        for directory in directories:
            self.recursive_delete(os.path.join(root, directory))
        for f in files:
            default_storage.delete(os.path.join(root, f))

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("ScormXBlock",
             """<vertical_demo>
                <scormxblock/>
                </vertical_demo>
             """),
        ]
