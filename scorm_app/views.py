# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.test import RequestFactory
from django.urls import reverse
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import status, views
from rest_framework.response import Response
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

from lms.djangoapps.courseware.module_render import _invoke_xblock_handler
from lms.djangoapps.mobile_api.decorators import mobile_course_access, mobile_view


@mobile_view()
class SyncXBlockData(views.APIView):

    def post(self, request, format=None):
        # TODO: need to take a handler from the request
        user = request.user
        handler = 'scorm_set_values'
        response_context = {}

        for course_data in request.data.get('courses_data'):
            course_id = course_data.get('course_id')
            response_context[course_id] = {}
            try:
                course_key = CourseKey.from_string(course_id)
            except InvalidKeyError:
                return Response({'error': '{} is not a valid course key'.format(course_id)},
                                status=status.HTTP_404_NOT_FOUND)

            with modulestore().bulk_operations(course_key):
                try:
                    course = modulestore().get_course(course_key)
                except ItemNotFoundError:
                    return Response({'error': '{} does not exist in the modulestore'.format(course_id)},
                                    status=status.HTTP_404_NOT_FOUND)

            for scorm in course_data.get('xblocks_data'):
                factory = RequestFactory()
                data = json.dumps(scorm)

                scorm_request = factory.post(reverse('scorm_app:set_values'), data,
                                             content_type='application/json')
                scorm_request.user = user
                scorm_request.session = request.session
                scorm_request.user.known = True

                usage_id = scorm.get('usage_id')
                scorm_response = _invoke_xblock_handler(scorm_request, course_id, usage_id, handler, None,
                                                        course=course)
                response_context[course_id][usage_id] = json.loads(scorm_response.content)
        return Response(response_context)
