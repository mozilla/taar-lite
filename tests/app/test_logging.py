from taar_lite.app.production import TaarLiteAppResource


def test_logging(test_context):
    app = TaarLiteAppResource(test_context)

    # These would error out if the object type was incorrect
    app.logger.error('foo')
    app.logger.warn('bar')
    app.logger.info('foo')
    app.logger.debug('bar')
