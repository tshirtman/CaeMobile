'''
Mock interface to return pre-recorded answers to requests.

'''
from json import JSONDecoder, JSONEncoder
JDECODE = JSONDecoder().decode
JENCODE = JSONEncoder().encode


class Mock(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


def get_answer(path, req_body, **kwargs):
    if path.endswith('login'):
        return mock_login(req_body)

    elif path.endswith('expenseoptions'):
        return mock_expenseoptions(req_body)

    print path, req_body, kwargs
    return True, None, Mock()


def mock_login(body):
    body = JDECODE(body)
    resp = {}
    if body['login'] == 'test' and body['password'] == 'test':
        resp['status'] = 'success'
        req = Mock(resp_status=200)
    else:
        resp['status'] = 'success'
        req = Mock(resp_status=401)

    return resp['status'] == 'success', req, resp


def mock_expenseoptions(body):
    print body

    #import pudb; pudb.set_trace()
    return True, Mock(resp_status=200), {
        "status": "success",
        "result": {
            "kmtypes": [
                {"amount": 1.25, "value": "3", "label": "Scooter"},
                {"amount": 1.28, "value": "4", "label": "Voiture"}],
            "expensetypes": [
                {"value": "5", "label": "Restauration"},
                {"value": "6", "label": "Fournitures"}],
            "teltypes": [
                {"percentage": 80, "value": "1", "label": "Mobile"},
                {"percentage": 80, "value": "2", "label": "Fixe + Adsl"}],
            "categories": [
                {"value": "1", "label": "Frais direct de fonctionnement"},
                {"value": "2", "label": "Frais concernant directement votre "
                    "activit\u00e9 aupr\u00e8s de vos clients"}]
            }
        }
