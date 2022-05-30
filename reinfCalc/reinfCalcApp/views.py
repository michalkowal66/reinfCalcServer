from django.views.generic import TemplateView, ListView
from django.middleware.csrf import get_token
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts import models
from calcEngine import engine
import json


# Create your views here.
class IndexView(TemplateView):
    template_name = 'index.html'


class AboutView(TemplateView):
    template_name = 'about.html'


class ContactView(TemplateView):
    template_name = 'contact.html'


class SourcesView(TemplateView):
    template_name = 'sources.html'


class ProfileInfoView(LoginRequiredMixin, TemplateView):
    context_object_name = 'user'
    template_name = 'reinfCalcApp/user_profile.html'


class ResultsListView(LoginRequiredMixin, ListView):
    model = models.Task
    template_name = 'reinfCalcApp/results.html'

    def get_queryset(self):
        tasks_query = self.model.objects.filter(owner=self.request.user).order_by('-creation_date')
        tasks = []

        for task_enum in enumerate(tasks_query):
            task_id = task_enum[0]
            task = task_enum[1]

            task_results = json.loads(task.results)

            task_dict = {
                'id': task_id+1,
                'element_type': task.element_type,
                'results': task_results,
            }

            tasks.append(task_dict)

        return tasks


class ResultsReportView(LoginRequiredMixin, ListView):
    model = models.Task
    context_object_name = 'task'

    def get_template_names(self):
        if self.task_id > len(self.task_object_query) or self.task_id <= 0:
            raise Http404

        element_type = self.task_object.element_type
        return [f'reports/{element_type}_report.html']

    def get_queryset(self):
        self.task_object_query = self.model.objects.filter(owner=self.request.user).order_by('-creation_date')
        self.task_id = self.kwargs['task_id']

        if self.task_id > len(self.task_object_query) or self.task_id <= 0:
            return None

        self.task_object = self.task_object_query[self.task_id - 1]
        task_parameters = json.loads(self.task_object.results)

        return task_parameters


def auth_app_user(request):
    user_agent = request.headers['User-Agent']
    if user_agent.startswith('python-requests'):
        if request.method == 'POST':
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return HttpResponse('authenticated')
            else:
                return HttpResponseForbidden('wrong username or password')

        response = HttpResponse(get_token(request))
        return response

    raise Http404


@login_required
def run_calculation(request):
    user_agent = request.headers['User-Agent']
    if user_agent.startswith('python-requests'):
        if request.method == 'POST':
            task_parameters = json.loads(request.POST.get('task_parameters'))
            current_user = models.User.objects.get(pk=request.user.id)

            element_type = task_parameters['element'][:-4]
            ElementClass = engine.dispatcher[element_type]
            rc_element = ElementClass(task_parameters)

            calculation_results = rc_element.calc_reinforcement()

            response_dict = json.dumps(calculation_results['results'])
            results_json_string = json.dumps(calculation_results['parameters'])

            task = models.Task(owner=current_user, element_type=element_type, results=results_json_string)
            task.save()

            return HttpResponse(response_dict, content_type='application/json')

        response = HttpResponse(get_token(request))
        return response

    raise Http404
