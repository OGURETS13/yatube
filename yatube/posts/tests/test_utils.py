import os
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

TEMP_MEDIA_ROOT = tempfile.mkdtemp(
    dir=os.path.join(settings.BASE_DIR, 'tmp')
)

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

uploaded_image = SimpleUploadedFile(
    name='small.gif',
    content=small_gif,
    content_type='image/gif'
)
