
from django import http

import utils


def queue_repos(request):
    scheduled, total = utils.queue_repos(request.body.split("\n"))
    return http.HttpResponse(utils.format_res(scheduled, total))


def queue_user(request, login):
    try:
        scheduled, total = utils.queue_user(login)
    except ValueError:
        raise http.Http404
    return http.HttpResponse(utils.format_res(scheduled, total))
