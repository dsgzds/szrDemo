# encoding: utf8

import logging
from copy import deepcopy
from functools import wraps
from sqlalchemy import inspect, func, desc

from pyutil.data.db.session import open_session, Session


class BaseModel(object):

    def _attr_filter(self, attr):
        if attr.startswith('_') or attr == 'is_del' or attr == 'create_time' or attr == 'update_time':
            return False

        return True
    
    def to_dict(self):
        attrs = self.columns()
        attr_dict = {}
        for attr in attrs:
            if not self._attr_filter(attr):
                continue
            if attr.endswith('time'):
                attr_dict[attr] = getattr(self, attr).strftime('%Y-%m-%d %H:%M:%S')
            elif attr == 'date':
                attr_dict[attr] = getattr(self, attr).strftime('%Y-%m-%d')
            else:
                attr_dict[attr] = getattr(self, attr)

        return attr_dict


    def columns(self):
        return list(filter(self._attr_filter, inspect(self.__class__).all_orm_descriptors.keys()))

    def add_model(self, data):
        columns = self.columns()
        for k, v in data.items():
            if k in columns:
                try:
                    setattr(self, k, v)
                except Exception as err:
                    logging.error(err)
                    raise


    def modify(self, data):
        for k, v in data.items():
            if k in self.modified_column:
                setattr(self, k, v)


def atomicity(commit=False):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            session = kwargs.get('session')
            if not session:
                with open_session(Session, commit=commit) as session:
                    kwargs['session'] = session
                    r = func(*args, **kwargs)
            else:
                r = func(*args, **kwargs)
            return r
        return decorator
    return wrapper


class ModelManager(object):

    def __init__(self, model):
        self.model = model

    @atomicity()
    def get(self, model_id, session=None):
        model = session.query(self.model).get(model_id)

        if not model or model.is_del == 1:
            return -1

        return model


    @atomicity(commit=True)
    def update(self, model_id, attr_change=None, operation='', user_id=0, session=None, **kwargs):
        if not operation:
            operation = 'update'
        if not attr_change:
            attr_change = {}
        attr_change.update(kwargs)

        model = session.query(self.model).filter_by(id=model_id).scalar()

        if not model or (operation != 'restore' and model.is_del == 1):
            return -1

        for k, v in attr_change.items():
            if k in model.modified_column:
                setattr(model, k, v)

            # 删除时删除关联表记录
            if k == 'is_del' and hasattr(self.model, 'delete_relate'):
                for relate_model, field in self.model.delete_relate:
                    self._del_rel(session, relate_model, field, [model.id])

        session.add(model)

        return model_id

    @atomicity(commit=True)
    def delete_by_query(self, filters=None, session=None, **kwargs):

        if filters == None:
            new_filters = {}
        else:
            new_filters = deepcopy(filters)

        new_filters.update(kwargs)

        query = session.query(self.model)
        query = self.search_filter(query, new_filters)

        models = query.all()
        for model in models:
            model.is_del = 1
            session.add(model)

        return

    # 递归删除关联的记录
    def _del_rel(self, session, model, field, ids):
        for model_id in ids:
            session.query(model).filter(getattr(model, field)==model_id)\
                        .update({'is_del': 1})

            if hasattr(model, 'delete_relate'):
                r_ids = session.query(model.id).filter(getattr(model, field)==model_id).all()
                if not r_ids:
                    return

                r_ids = [r[0] for r in r_ids]
                for relate_model, field, in model.delete_relate:
                    self._del_rel(session, relate_model, field, r_ids)


    @atomicity(commit=True)
    def add(self, data, session=None):
        if not data:
            return -1

        if not isinstance(data, list):
            data = [data]
        model_ids = []

        for d in data:
            model = self.model()
            model.add_model(d)
            session.add(model)
            session.flush()

            model_ids.append(model.id)

        if len(model_ids) < 2:
            return model_ids[0]
        else:
            return model_ids


    @atomicity(commit=True)
    def delete(self, model_id, session=None):
        res = self.update(model_id, operation='delete', is_del=1, session=session)

        return res


    def search_filter(self, query, filters):
        for k, v in filters.items():

            # if v != 0 and not v:
            #     continue

            if isinstance(v, str):
                v = v.strip()

            if isinstance(v, list):
                query = query.filter(getattr(self.model, k).in_(v))
                continue

            if k == 'start_time':
                query = query.filter(self.model.create_time>=datetime.strptime(v, '%Y%m%d%H%M%S'))

            elif k == 'end_time':
                query = query.filter(self.model.create_time<=datetime.strptime(v, '%Y%m%d%H%M%S'))

            elif k == 'start_date':
                query = query.filter(self.model.date >= v)

            elif k == 'end_date':
                query = query.filter(self.model.date <= v)

            # elif getattr(self.model, k).type.python_type == str:
            #     value_pattern = '%{}%'.format(str(v))
            #     query = query.filter(getattr(self.model, k).like(value_pattern))

            else:
                query = query.filter(getattr(self.model, k)==v)

        return query


    @atomicity()
    def search(self, filters=None, offset=0, limit=-1, not_del=True, sort='desc', session=None, **kwargs):

        if filters == None:
            new_filters = {}
        else:
            new_filters = deepcopy(filters)

        new_filters.update(kwargs)

        query = session.query(self.model)

        query = self.search_filter(query, new_filters)

        if not_del and hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)

        total = query.with_entities(func.count(self.model.id)).scalar()
        if sort != 'asc':
            query = query.order_by(desc(self.model.id))

        if limit != -1:
            query = query.offset(offset).limit(limit)

        models = query.all()

        return models, total


    @atomicity()
    def get_total(self, filters=None, not_del=True, session=None, **kwargs):
        if filters == None:
            new_filters = {}
        else:
            new_filters = deepcopy(filters)

        new_filters.update(kwargs)

        query = session.query(self.model)

        query = self.search_filter(query, new_filters)

        if not_del and hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)
        total = query.with_entities(func.count(self.model.id)).scalar()

        return total


    @atomicity()
    def search_all(self, filters=None, sort='desc', session=None, **kwargs):
        if filters == None:
            filters = {}

        filters.update(kwargs)

        query = session.query(self.model)

        for k, v in filters.items():
            if k.endswith('[]'):
                query = query.filter(getattr(self.model, k[:-2]).in_(v))

            elif getattr(self.model, k).type.python_type == str:
                value_pattern = '%{}%'.format(str(v))
                query = query.filter(getattr(self.model, k).like(value_pattern))

            else:
                query = query.filter(getattr(self.model, k)==v)

        total = query.with_entities(func.count(self.model.id)).scalar()
        if sort != 'asc':
            query = query.order_by(desc(self.model.id))

        models = query.all()

        return models, total

    @atomicity()
    def search_precise(self, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}

        filters.update(kwargs)

        query = session.query(self.model).filter_by(is_del=0)

        for k, v in filters.items():
            query = query.filter(getattr(self.model, k)==v)

        models = query.all()

        return models

    @atomicity()
    def search_field(self, dist_field, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}
        filters.update(kwargs)

        query = session.query(getattr(self.model, dist_field))
        if hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)

        query = self.search_filter(query, filters)
        results = query.all()

        results = [r[0] for r in results]

        return results


    @atomicity()
    def search_fields(self, dist_fields, filters=None, session=None, **kwargs):
        if filters == None:
            filters = {}
        filters.update(kwargs)

        field_list = dist_fields.split(',')
        query_list = [getattr(self.model, field) for field in field_list]

        query = session.query(*query_list)
        if hasattr(self.model, 'is_del'):
            query = query.filter_by(is_del=0)

        query = self.search_filter(query, filters)
        results = query.all()

        return results


    @atomicity()
    def get_id_not_del(self, session=None):
        r = session.query(func.min(self.model.id)).filter_by(is_del=0).scalar()
        
        return r

    @atomicity()
    def det_id_del(self, session=None):
        r = session.query(func.min(self.model.id)).filter_by(is_del=1).scalar()

        return r

    @atomicity()
    def get_all(self, model_id, session=None):
        model = session.query(self.model).get(model_id)

        return model

