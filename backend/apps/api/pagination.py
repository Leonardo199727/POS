from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    """
    Pagination renderer that strictly complies with the POS financial frontend structure.
    Returns the objects directly inside "data" array to prevent breaking the existing
    `res.data.data` contract on React, and appends control fields into "meta".
    """
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': data,
            'meta': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            }
        })
