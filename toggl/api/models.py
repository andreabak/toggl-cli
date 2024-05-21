import json
import logging
import typing
from copy import copy
from urllib.parse import quote_plus
from validate_email import validate_email

import datetime
import pendulum

from toggl.api import base, fields
from toggl import utils, exceptions

logger = logging.getLogger('toggl.api.models')


_T = typing.TypeVar("_T")
ValueOrCollection = typing.Union[typing.Collection[_T], _T]


# Organization entity
class Organization(base.TogglEntity):
    _endpoints_name = "organizations"
    _can_create = False  # TODO: check
    _can_delete = False  # TODO: check

    name = fields.StringField(required=True)
    """
    Name of the organization
    """

    admin = fields.BooleanField()
    """
    Shows whether the current request user is an admin of the organization
    """

    at = fields.StringField()
    """
    Organization's last modification date
    """

    created_at = fields.StringField()
    """
    Organization's creation date
    """

    is_multi_workspace_enabled = fields.BooleanField()
    """
    Is true when the organization option is_multi_workspace_enabled is set
    """

    is_unified = fields.BooleanField()

    max_data_retention_days = fields.IntegerField()
    """
    How far back free workspaces in this org can access data.
    """

    max_workspaces = fields.IntegerField()
    """
    Maximum number of workspaces allowed for the organization
    """

    owner = fields.BooleanField()
    """
    Whether the requester is a the owner of the organization
    """

    payment_methods = fields.StringField()
    """
    Organization's subscription payment methods. Omitted if empty.
    """

    permissions = fields.StringField()

    pricing_plan_enterprise = fields.BooleanField()
    """
    The subscription plan is an enterprise plan
    """

    pricing_plan_id = fields.IntegerField()  # TODO: map entity?
    """
    Organization plan ID
    """

    pricing_plan_name = fields.StringField()
    """
    The subscription plan name the org is currently on. Free or any plan name coming from payment provider
    """

    server_deleted_at = fields.StringField()
    """
    Organization's delete date
    """

    suspended_at = fields.StringField()
    """
    Whether the organization is currently suspended
    """

    user_count = fields.IntegerField()
    """
    Number of organization users
    """

    def invite(self, workspace, *emails, admin=False, role=None):  # type: (Workspace, typing.Collection[str], bool, typing.Optional[str]) -> None
        """
        Invites users defined by email addresses. The users does not have to have account in Toggl, in that case after
        accepting the invitation, they will go through process of creating the account in the Toggl web.

        :param workspace: The workspace to invite users to.
        :param emails: List of emails to invite.
        :param admin: Whether the invited users should be admins.
        :param role: Role of the invited users.
        :return: None
        """
        for email in emails:
            if not validate_email(email):
                raise exceptions.TogglValidationException(f'Supplied email \'{email}\' is not valid email!')

        workspace_invite_data = {'workspace_id': workspace.id, 'admin': admin}
        if role:
            workspace_invite_data['role'] = role
        emails_json = json.dumps({'emails': emails, 'workspaces': [workspace_invite_data]})
        data = utils.toggl("/organizations/{}/invitations".format(self.id), "post", emails_json, config=self._config)

        # FIXME: remove, error handling is done by status code
        # if 'messages' in data and data['messages']:
        #     raise exceptions.TogglException(data['messages'])

        # TODO: return something?


class WorkspaceToggleSet(base.TogglSet):
    """
    Specialized TogglSet for workspace entities (not to be confused with :class:`base.WorkspacedTogglSet`
    """

    def build_detail_url(self, eid, config, conditions):  # type: (int, utils.Config, typing.Dict) -> str
        return '/{}/{}'.format(self.entity_endpoints_name, eid)


# Workspace entity
class Workspace(base.TogglEntity):
    _endpoints_name = "workspaces"
    _can_create = False
    _can_delete = False

    name = fields.StringField(required=True)
    """
    Name of the workspace
    """

    premium = fields.BooleanField()
    """
    If it's a pro workspace or not. Shows if someone is paying for the workspace or not
    """

    admin = fields.BooleanField()
    """
    Shows whether currently requesting user has admin access to the workspace
    """

    only_admins_may_create_projects = fields.BooleanField()
    """
    Whether only the admins can create projects or everybody
    """

    only_admins_may_create_tags = fields.BooleanField()
    """
    Whether only the admins can create tags or everybody
    """

    only_admins_see_billable_rates = fields.BooleanField()
    """
    Whether only the admins can see billable rates or everybody
    """

    only_admins_see_team_dashboard = fields.BooleanField()
    """
    Whether only the admins can see team dashboard or everybody
    """

    rounding = fields.IntegerField()
    """
    Type of rounding:

    * round down: -1
    * nearest: 0
    * round up: 1
    """

    rounding_minutes = fields.IntegerField()
    """
    Round up to nearest minute
    """

    default_hourly_rate = fields.FloatField()
    """
    Default hourly rate for workspace, won't be shown to non-admins
    if the only_admins_see_billable_rates flag is set to true
    """

    default_currency = fields.StringField()
    """
    Default currency for workspace
    """

    ical_enabled = fields.BooleanField()
    ical_url = fields.StringField()
    logo_url = fields.StringField()

    # As TogglEntityMeta is by default adding WorkspacedTogglSet to TogglEntity,
    # but we want WorkspaceToggleSet so defining it here explicitly.
    objects = WorkspaceToggleSet()


class WorkspacedEntity(base.TogglEntity):
    """
    Abstract entity which has linked Workspace
    """

    workspace = fields.MappingField(Workspace, 'workspace_id', write=False,
                                               default=lambda config: config.default_workspace) # type: Workspace
    """
    Workspace to which the resource is linked to.
    """

    def get_url(self):  # type: () -> str
        return f'workspaces/{self.workspace.id}/{self.get_endpoints_name()}'


# Premium Entity
class PremiumEntity(WorkspacedEntity):
    """
    Abstract entity that enforces that linked Workspace is premium (paid).
    """

    def save(self, config=None):  # type: (utils.Config) -> None
        if not self.workspace.premium:
            raise exceptions.TogglPremiumException(f'The entity {self.get_name(verbose=True)} requires to be associated with Premium workspace!')

        super().save(config)


# ----------------------------------------------------------------------------
# Entities definitions
# ----------------------------------------------------------------------------
class Client(WorkspacedEntity):
    """
    Client entity
    """

    _endpoints_name = "clients"

    name = fields.StringField(required=True)
    """
    Name of client (Required)
    """

    notes = fields.StringField()



class Project(WorkspacedEntity):
    """
    Project entity
    """

    _endpoints_name = "projects"

    name = fields.StringField(required=True)
    """
    Name of the project. (Required)
    """

    client = fields.MappingField(Client, 'client_id')
    """
    Client associated to the project.
    """

    active = fields.BooleanField(default=True)
    """
    Whether the project is archived or not. (Default: True)
    """

    is_private = fields.BooleanField(default=True)
    """
    Whether project is accessible for only project users or for all workspace users. (Default: True)
    """

    billable = fields.BooleanField(premium=True)
    """
    Whether the project is billable or not.

    (Available only for Premium workspaces)
    """

    auto_estimates = fields.BooleanField(default=False, premium=True)
    """
    Whether the estimated hours are automatically calculated based on task estimations or manually
    fixed based on the value of 'estimated_hours'.

    (Available only for Premium workspaces)
    """

    estimated_hours = fields.IntegerField(default=0, premium=True)
    """
    If auto_estimates is true then the sum of task estimations is returned, otherwise user inserted hours.

    (Available only for Premium workspaces)
    """

    color = fields.StringField()
    """
    Hex code of the color selected for the project
    """

    rate = fields.FloatField(premium=True)
    """
    Hourly rate of the project.

    (Available only for Premium workspaces)
    """

    def add_user(self, user, manager=False, rate=None) :  # type: (User, bool, typing.Optional[float]) -> ProjectUser
        """
        Add new user to a project.

        :param user: User to be added
        :param manager: Specifies if the user should have manager's rights
        :param rate: Rate for billing
        :return: ProjectUser instance.
        """
        project_user = ProjectUser(project=self, user=user, workspace=self.workspace, manager=manager, rate=rate)
        project_user.save()

        return project_user


class UserSet(base.WorkspacedTogglSet):

    def current_user(self, config=None):  # type: (utils.Config) -> 'User'
        """
        Fetches details about the current user.
        """
        fetched_entity = utils.toggl('/me', 'get', config=config)
        return self.entity_cls.deserialize(config=config, **fetched_entity)


class User(WorkspacedEntity):
    """
    User entity.
    """

    _endpoints_name = "users"
    _can_create = False
    _can_update = False
    _can_delete = False
    _can_get_detail = False

    api_token = fields.StringField()
    """
    API token to use for API calls.

    (Returned only for User.objects.current_user() call.)
    """

    has_password = fields.BooleanField()
    country_id = fields.StringField()
    intercom_hash = fields.StringField()
    openid_email = fields.StringField()
    openid_enabled = fields.BooleanField()

    default_workspace = fields.MappingField(Workspace, 'default_workspace_id')  # type: Workspace
    """
    Default workspace for calls that does not specify Workspace.

    (Returned only for User.objects.current_user() call.)
    """

    email = fields.EmailField()
    """
    Email address of user.
    """

    fullname = fields.StringField()
    """
    Full name of the user.
    """

    beginning_of_week = fields.ChoiceField({
        '0': 'Sunday',
        '1': 'Monday',
        '2': 'Tuesday',
        '3': 'Wednesday',
        '4': 'Thursday',
        '5': 'Friday',
        '6': 'Saturday'
    })
    """
    Defines which day is the first day of week for the user.
    """

    language = fields.StringField()
    """
    Stores language used for the user.
    """

    image_url = fields.StringField()
    """
    URL of the profile image of the user.
    """

    timezone = fields.StringField()
    """
    Timezone which is used to convert the times into.

    May differ from one used in this tool, see toggl.utils.Config().
    """

    objects = UserSet()

    @classmethod
    def signup(cls, email, password, timezone=None, created_with='TogglCLI',
               config=None):  # type: (str, str, str, str, utils.Config) -> User
        """
        Creates brand new user. After creation confirmation email is sent to him.

        :param email: Valid email of the new user.
        :param password: Password of the new user.
        :param timezone: Timezone to be associated with the user. If empty, than timezone from config is used.
        :param created_with: Name of application that created the user.
        :param config:
        :return:
        """
        if config is None:
            config = utils.Config.factory()

        if timezone is None:
            timezone = config.timezone

        if not validate_email(email):
            raise exceptions.TogglValidationException('Supplied email \'{}\' is not valid email!'.format(email))

        user_json = json.dumps({'user': {
            'email': email,
            'password': password,
            'timezone': timezone,
            'created_with': created_with
        }})
        data = utils.toggl("/signup", "post", user_json, config=config)
        return cls.deserialize(config=config, **data)

    def is_admin(self, workspace):
        wid = workspace.id if isinstance(workspace, Workspace) else workspace

        workspace_user = WorkspaceUser.objects.get(wid=wid, uid=self.id)
        return workspace_user.admin

    def __str__(self):
        return '{} (#{})'.format(self.fullname, self.id)


class WorkspaceUser(WorkspacedEntity):
    """
    Workspace User entity.

    This entity represents assignment of specific User into Workspace.
    It additionally configures access rights and several other things.
    """

    _endpoints_name = "workspace_users"
    _can_get_detail = False
    _can_create = False

    email = fields.EmailField(write=False)
    """
    Email of the user.
    """

    active = fields.BooleanField()
    """
    If user is active in Workspace.
    """

    admin = fields.BooleanField(admin_only=True)
    """
    Weather user has admin privilege in the Workspace.
    """

    user = fields.MappingField(User, 'uid', write=False)
    """
    User's instance
    """

    def __str__(self):
        return '{} (#{})'.format(self.email, self.id)


class ProjectUser(WorkspacedEntity):
    """
    Project User entity.

    Similarly to WorkspaceUser, it is entity which represents assignment of specific User into Project.
    It additionally configures access rights and several other things.
    """

    _endpoints_name = "project_users"
    _can_get_detail = False

    rate = fields.FloatField(admin_only=True)
    """
    Hourly rate for the project user in the currency of the project's client or in workspace default currency.

    (Available only for Premium workspaces)
    """

    manager = fields.BooleanField(default=False)
    """
    Admin rights for this project
    """

    project = fields.MappingField(Project, 'pid', write=False)
    """
    Project to which the User is assigned.
    """

    user = fields.MappingField(User, 'uid', write=False)
    """
    User which is linked to Project.
    """

    def __str__(self):
        return '{}/{} (#{})'.format(self.project.name, self.user.email, self.id)


class Task(PremiumEntity):
    """
    Task entity.

    This entity is available only for Premium workspaces.
    """

    _endpoints_name = "tasks"

    name = fields.StringField(required=True)
    """
    Name of task
    """

    project = fields.MappingField(Project, 'pid', required=True)
    """
    Project to which the Task is linked to.
    """

    user = fields.MappingField(User, 'uid')
    """
    User to which the Task is assigned to.
    """

    estimated_seconds = fields.IntegerField()
    """
    Estimated duration of task in seconds.
    """

    active = fields.BooleanField(default=True)
    """
    Whether the task is done or not.
    """

    tracked_seconds = fields.IntegerField(write=False)
    """
    Total time tracked (in seconds) for the task.
    """


class Tag(WorkspacedEntity):
    """
    Tag entity
    """

    _endpoints_name = "tags"
    _can_get_detail = False

    name = fields.StringField(required=True)
    """
    Name of tag (Required)
    """


# Time Entry entity


class TimeEntryDateTimeField(fields.DateTimeField):
    """
    Special extension of DateTimeField which handles better way of formatting the datetime for CLI use-case.
    """

    def format(self, value, config=None, instance=None, display_running=False,
               only_time_for_same_day=None):
        if not display_running and not only_time_for_same_day:
            return super().format(value, config)

        if value is None and display_running:
            return 'running'

        if instance is not None and only_time_for_same_day:
            config = config or utils.Config.factory()

            if value.in_timezone(config.timezone).to_date_string() == only_time_for_same_day.in_timezone(
                config.timezone).to_date_string():
                return value.in_timezone(config.timezone).format(config.time_format)

        return super().format(value, config)


def get_duration(name, instance):  # type: (str, base.Entity) -> int
    """
    Getter for Duration Property field.

    Handles correctly the conversion of negative running duration (for more refer to the Toggl API doc).
    """
    if instance.is_running:
        return instance.start.int_timestamp * -1

    return int((instance.stop.replace(microsecond=0) - instance.start.replace(microsecond=0)).in_seconds())


def set_duration(name, instance, value, init=False):  # type: (str, base.Entity, typing.Optional[int], bool) -> typing.Optional[bool]
    """
    Setter for Duration Property field.
    """
    if init is True:
        instance.is_running = False

    if value is None:
        return

    if value > 0:
        instance.is_running = False
        instance.stop = instance.start + pendulum.duration(seconds=value)
    elif value == 0:
        instance.is_running = False
    else:
        instance.is_running = True
        instance.stop = None

    return True  # Any change will result in updated instance's state.


def format_duration(value, config=None):  # type: (typing.Optional[int], utils.Config) -> typing.Optional[str]
    """
    Formatting the duration into HOURS:MINUTES:SECOND format.
    """
    if value is None:
        return None

    if value < 0:
        config = config or utils.Config.factory()
        value = pendulum.now(tz=config.tz).int_timestamp + value

    hours = value // 3600
    minutes = (value - hours * 3600) // 60
    seconds = (value - hours * 3600 - minutes * 60) % 60

    return '{}:{:02d}:{:02d}'.format(hours, minutes, seconds)


datetime_type = typing.Union[datetime.datetime, pendulum.DateTime]


class TimeEntrySet(base.WorkspacedTogglSet):
    """
    TogglSet which is extended by current() method which returns the currently running TimeEntry.
    Moreover it extends the filtrating mechanism by native filtering according start and/or stop time.
    """

    def build_list_url(self, caller, config, conditions):  # type: (str, utils.Config, typing.Dict) -> str
        url = '/me/{}'.format(self.entity_endpoints_name)

        if caller == 'filter':
            start = conditions.pop('start', None)
            stop = conditions.pop('stop', None)

            if start is not None or stop is not None:
                url += '?'

            if start is not None:
                url += 'start_date={}&'.format(quote_plus(start.isoformat()))

            if stop is not None:
                url += 'end_date={}&'.format(quote_plus(stop.isoformat()))

        return url

    def build_detail_url(self, eid, config, conditions):  # type: (int, utils.Config, typing.Dict) -> str
        return '/me/{}/{}'.format(self.entity_endpoints_name, eid)

    def _fetch_all(self, url, order, config):  # type: (str, str, utils.Config) -> typing.List[base.Entity]
        output = super()._fetch_all(url, order, config)
        output.sort(key=lambda e: e.start, reverse=(order == 'desc'))
        return output

    def current(self, config=None):  # type: (utils.Config) -> typing.Optional[TimeEntry]
        """
        Method that returns currently running TimeEntry or None if there is no currently running time entry.

        :param config:
        :return:
        """
        config = config or utils.Config.factory()
        fetched_entity = utils.toggl('/me/time_entries/current', 'get', config=config)

        if fetched_entity is None:
            return None

        return self.entity_cls.deserialize(config=config, **fetched_entity)

    def _prepare_reports_request(
        self,
        start,
        stop,
        first_row_number,
        wid,
        clients=None,
        projects=None,
        users=None,
        tags=None,
        tasks=None,
        time_entries=None,
        description=None,
        rounding=None,
        order_by=None,
        order_direction=None,
    ):  # type: (datetime.datetime, datetime.datetime, int, int, typing.Optional[ValueOrCollection[typing.Union[Client, int]]], typing.Optional[ValueOrCollection[typing.Union[Project, int]]], typing.Optional[ValueOrCollection[typing.Union[User, int]]], typing.Optional[ValueOrCollection[typing.Union[Tag, int]]], typing.Optional[ValueOrCollection[typing.Union[Task, int]]], typing.Optional[ValueOrCollection[typing.Union["TimeEntry", int]]], typing.Optional[str], typing.Optional[bool], typing.Optional[typing.Literal["date", "user", "duration", "description", "last_update"]], typing.Optional[typing.Literal["asc", "desc", "ASC", "DESC"]]) -> (str, typing.Dict[str, typing.Any])
        url = f'/workspace/{wid}/search/time_entries'

        data = {
            "first_row_number": first_row_number or None,
        }
        if start is not None:
            data['start_date'] = start.date().isoformat()
        if stop is not None:
            data['end_date'] = stop.date().isoformat()

        def get_ids(entities):  # type: (ValueOrCollection[typing.Union[base.Entity, int]]) -> typing.List[int]
            if isinstance(entities, (base.TogglEntity, int)):
                entities = [entities]
            elif not isinstance(entities, typing.Collection):
                raise ValueError("Filtering entities must be one or more of entities or ids")
            ids = []
            for element in entities:
                if not isinstance(element, (base.TogglEntity, int)):
                    raise ValueError("Filtering entities must be one or more of entities or ids")
                ids.append(element.id if isinstance(element, base.TogglEntity) else element)
            return ids

        if clients is not None:
            data["client_ids"] = get_ids(clients)
        if projects is not None:
            data["project_ids"] = get_ids(projects)
        if tasks is not None:
            data["task_ids"] = get_ids(tasks)
        if tags is not None:
            data["tag_ids"] = get_ids(tags)
        if users is not None:
            data["user_ids"] = get_ids(users)
        if time_entries is not None:
            data["time_entry_ids"] = get_ids(time_entries)
        if description is not None:
            data["description"] = description
        if rounding is not None:
            data["rounding"] = rounding

        if order_by is not None:
            data["order_by"] = order_by
        if order_direction is not None:
            data["order_direction"] = order_direction.upper()

        return url, data

    def _generate_from_reports(self, config, group_dict, wid):  # type: (utils.Config, dict, int) -> typing.Iterator[TimeEntry]
        group_keys = {"description", "project_id", "task_id", "user_id", "tags_ids", "billable"}
        common_values = {
            "workspace_id": wid,
            **dict(filter(lambda kv: kv[0] in group_keys, group_dict.items()))
        }
        for entity in group_dict["time_entries"]:
            entity_values = {
                **common_values,
                "id": entity["id"],
                "start": entity["start"],
                "stop": entity["stop"],
            }
            entity = self.entity_cls.deserialize(config=config, **entity_values)
            entity.duration = get_duration("duration", entity)
            yield entity

    def all_from_reports(self, start=None, stop=None, workspace=None, config=None):  # type: (typing.Optional[datetime_type], typing.Optional[datetime_type], typing.Union[str, int, Workspace], typing.Optional[utils.Config]) -> typing.Generator[TimeEntry, None, None]
        return self.report_detailed(start=start, stop=stop, workspace=workspace, config=config)

    def report_detailed(self, start=None, stop=None, workspace=None, config=None, **conditions):  # type: (typing.Optional[datetime_type], typing.Optional[datetime_type], typing.Union[str, int, Workspace], typing.Optional[utils.Config], typing.Any) -> typing.Generator[TimeEntry, None, None]
        """
        Method that implements fetching of time entries through Report API.
        No limitation on number of time entries.

        :param start: From when time entries should be fetched. Defaults to today - 6 days.
        :param stop: Until when time entries should be fetched. Defaults to today, unless since is in future or more than year ago, in this case until is since + 6 days.
        :param workspace: Workspace from where should be the time entries fetched from. Defaults to Config.default_workspace.
        :param config: Config instance. Defaults to Config.factory().
        :param conditions: Additional filters that should be applied to fetching the time entries.
        :return: Generator that yields TimeEntry
        """
        from .. import toggl

        if start is None:
            start = (pendulum.now() - pendulum.duration(days=6)).start_of("day")
        if stop is None:
            stop = (start + pendulum.duration(days=7)).end_of("day")

        config = config or utils.Config.factory()
        first_row_number = 1

        if workspace is None:
            wid = config.default_workspace.id
        elif isinstance(workspace, Workspace):
            wid = workspace.id
        elif isinstance(workspace, int):
            wid = workspace
        else:
            try:
                wid = int(workspace)
            except (ValueError, TypeError):
                logger.exception("Couldn't infer workspace, falling back to default")
                wid = config.default_workspace.id

        while True:
            url, data = self._prepare_reports_request(start, stop, first_row_number, wid, **conditions)
            response = utils.toggl_request(url, 'post', data=json.dumps(data), config=config, address=toggl.REPORTS_URL)
            results = response.json()

            if not results:
                return

            for group in results:
                yield from self._generate_from_reports(config, group, wid)

            next_row_number = int(response.headers.get('X-Next-Row-Number', 0))
            if not next_row_number or next_row_number == first_row_number:
                return
            first_row_number = next_row_number


class TimeEntry(WorkspacedEntity):
    _endpoints_name = "time_entries"

    description = fields.StringField()
    """
    Description of the entry.
    """

    project = fields.MappingField(Project, 'project_id')
    """
    Project to which the Time entry is linked to.
    """

    task = fields.MappingField(Task, 'task_id', premium=True)
    """
    Task to which the Time entry is linked to.

    (Available only for Premium workspaces)
    """

    billable = fields.BooleanField(default=False, premium=True)
    """
    If available to be billed. (Default: False)

    (Available only for Premium workspaces)
    """

    start = TimeEntryDateTimeField(required=True)
    """
    DateTime of start of the time entry. (Required)
    """

    stop = TimeEntryDateTimeField()
    """
    DateTime of end of the time entry.
    """

    duration = fields.PropertyField(get_duration, set_duration, formatter=format_duration)
    """
    Dynamic field of entry's duration in seconds.

    If the time entry is currently running, the duration attribute contains a negative value,
    denoting the start of the time entry in seconds since epoch (Jan 1 1970). The correct duration can be
    calculated as current_time + duration, where current_time is the current time in seconds since epoch.
    """

    is_running = fields.BooleanField(default=False)
    """
    Whether the time entry is currently running.
    """

    created_with = fields.StringField(required=True, default='TogglCLI', read=False)
    """
    Information who created the time entry.
    """

    tags = fields.SetField()
    """
    Set of tags associated with the time entry.
    """

    # TODO: tags_ids

    objects = TimeEntrySet()

    def __init__(self, start, stop=None, duration=None, **kwargs):
        if stop is None and duration is None:
            raise ValueError(
                'You can create only finished time entries through this way! '
                'You must supply either \'stop\' or \'duration\' parameter!'
            )

        super().__init__(start=start, stop=stop, duration=duration, **kwargs)

    def to_dict(self, serialized=False, changes_only=False):
        # Enforcing serialize duration when start or stop changes
        if changes_only and (self.__change_dict__.get('start') or self.__change_dict__.get('stop')):
            self.__change_dict__['duration'] = None

        return super().to_dict(serialized=serialized, changes_only=changes_only)

    @classmethod
    def start_and_save(cls, start=None, config=None, **kwargs):  # type: (pendulum.DateTime, utils.Config, **typing.Any) -> TimeEntry
        """
        Creates a new running entry.

        If there is another running time entry in the time of calling this method, then the running entry is stopped.
        This is handled by Toggl's backend.

        :param start: The DateTime object representing start of the new TimeEntry. If None than current time is used.
        :param config:
        :param kwargs: Other parameters for creating the new TimeEntry
        :return: New running TimeEntry
        """
        config = config or utils.Config.factory()

        if start is None:
            start = pendulum.now(config.timezone)

        if 'stop' in kwargs or 'duration' in kwargs:
            raise RuntimeError('With start_and_save() method you can not create finished entries!')

        instance = cls.__new__(cls)
        instance.__change_dict__ = {}
        instance.is_running = True
        instance._config = config
        instance.start = start

        for key, value in kwargs.items():
            setattr(instance, key, value)

        instance.save()

        return instance

    def stop_and_save(self=None, stop=None):
        """
        Stops running the entry. It has to be running entry.

        :param stop: DateTime which should be set as stop time. If None, then current time is used.
        :return: Self
        """
        if self is None:
            # noinspection PyMethodFirstArgAssignment
            self = TimeEntry.objects.current()
            if self is None:
                raise exceptions.TogglValidationException('There is no running entry to be stoped!')

        if not self.is_running:
            raise exceptions.TogglValidationException('You can\'t stop not running entry!')

        config = self._config or utils.Config.factory()

        if stop is None:
            stop = pendulum.now(config.timezone)

        self.stop = stop
        self.is_running = False
        self.save(config=config)

        return self

    def continue_and_save(self, start=None):
        """
        Creates new time entry with same description as the self entry and starts running it.

        :param start: The DateTime object representing start of the new TimeEntry. If None than current time is used.
        :return: The new TimeEntry.
        """
        if self.is_running:
            logger.warning('Trying to continue time entry {} which is already running!'.format(self))

        config = self._config or utils.Config.factory()

        if start is None:
            start = pendulum.now(config.timezone)

        new_entry = copy(self)
        new_entry.start = start
        new_entry.stop = None
        new_entry.is_running = True

        new_entry.save(config=config)

        return new_entry

    def __str__(self):
        return '{} (#{})'.format(getattr(self, 'description', ''), self.id)
