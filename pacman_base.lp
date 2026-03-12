#const gsize = 5.
{ grid_node(X, Y) } :- X = 0..(gsize-1), Y = 0..(gsize-1).
{ actor(X, Y) } 1 :- X = 0..(gsize-1), Y = 0..(gsize-1).
{ goal(X, Y) } 1 :- X = 0..(gsize-1), Y = 0..(gsize-1).

twoactor(1) :- actor(A,B), actor(X,Y), A != X.
twoactor(1) :- actor(A,B), actor(X,Y), B != Y.
twogoal(1) :- goal(A,B), goal(X,Y), A != X.
twogoal(1) :- goal(A,B), goal(X,Y), B != Y.
node(X, Y) :- grid_node(X, Y).
edge(X, Y, X, YP) :- node(X, Y), node(X, YP), YP == Y + 1.
edge(X, Y, XP, Y) :- node(X, Y), node(XP, Y), XP == X + 1.
edge(X, Y, X, YP) :- node(X, Y), node(X, YP), YP == Y - 1.
edge(X, Y, XP, Y) :- node(X, Y), node(XP, Y), XP == X - 1.
path(X, Y, X, Y, 0) :- node(X, Y).
path(X, Y, XPP, YPP, N+1) :- path(X, Y, XP, YP, N), edge(XP, YP, XPP, YPP), N+1 < 25.
goal_path(N) :- path(A,B,X,Y,N), actor(A,B), goal(X,Y).
shortest_path(N) :- N = #min{X: goal_path(X)}, not twogoal(1), not twoactor(1).
shortest_path(17) :- twogoal(1).
shortest_path(17) :- twoactor(1).

:- twoactor(1).
:- twogoal(1).
:- shortest_path(#sup).

#show actor/2.
#show grid_node/2.
#show goal/2.
#show shortest_path/1.
